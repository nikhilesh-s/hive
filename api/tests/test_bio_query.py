"""Deterministic biological query generator: parse cases, sql_guard
compatibility, and injection resistance. The generator gets NO special trust —
everything it emits must survive guard_and_limit_sql like the LLM path."""

import sqlglot
from app.bio_query import generate_bio_sql
from app.sql_guard import guard_and_limit_sql
from sqlglot import exp


def _guarded(q: str) -> str:
    return guard_and_limit_sql(generate_bio_sql(q), 100)


def test_phospho_site_query():
    sql = generate_bio_sql("phospho STAT3 Tyr705")
    assert "modification_type ILIKE '%phospho%'" in sql
    assert "residue ILIKE 'Tyr' AND residue_position = 705" in sql
    assert "%STAT3%" in sql  # remaining term matched across bio columns
    assert "Tyr705" not in sql.replace("residue", "")  # site consumed, not a term
    _guarded("phospho STAT3 Tyr705")  # must pass the guard


def test_one_letter_site():
    sql = generate_bio_sql("phospho AKT S473")
    assert "residue ILIKE 'Ser' AND residue_position = 473" in sql
    assert "%akt([^a-z]%)?" in sql


def test_vendor_catalog():
    sql = generate_bio_sql("CST 9145")
    assert "antibody_vendor ILIKE '%cell signaling%'" in sql
    assert "antibody_catalog_number ILIKE '%9145%'" in sql
    _guarded("CST 9145")


def test_hash_catalog_without_vendor():
    sql = generate_bio_sql("antibody #9134")
    assert "antibody_catalog_number ILIKE '%9134%'" in sql


def test_bare_number_without_vendor_is_not_catalog():
    # A number with no vendor and no '#' is NOT a catalog filter of its own
    # (it is only one of the OR'd columns of a plain term).
    sql = generate_bio_sql("9145")
    assert "WHERE antibody_catalog_number" not in sql and " AND antibody_catalog_number" not in sql
    for q in ("HEK 293 CST", "CST 1:1000"):   # a cell line or a dilution next to a vendor is not a catalog
        sql = generate_bio_sql(q)
        assert "AND antibody_catalog_number" not in sql and "%1000%" not in sql, q
        _guarded(q)


def test_row_cap_drops_the_partial_last_experiment(monkeypatch):
    import asyncio

    from app import search_service
    rows = [{"id": i, "paper_id": "10.1/x", "doi": "10.1/x", "target": "STAT3", "stable_row_key": f"e{i // 5}:{i}"}
            for i in range(12)]                     # experiments e0, e1 (5 lanes) and e2 (2 of its lanes)

    async def fake_query(sql):
        return rows
    monkeypatch.setattr(search_service, "run_readonly_query", fake_query)
    monkeypatch.setattr(search_service.settings, "openai_key", "")   # deterministic parser, never a model call
    out = asyncio.run(search_service.execute_search("STAT3", 12))
    assert out.truncated and out.count == 10 and {r.stable_row_key.split(":")[0] for r in out.results} == {"e0", "e1"}
    out = asyncio.run(search_service.execute_search("STAT3", 100))
    assert not out.truncated and out.count == 12


def test_non_numeric_catalog_numbers():
    # Regression: only digit catalogs parsed, so these found 0 of 50/31/53/31 corpus rows.
    for q, cat in (("Sigma A1978", "A1978"), ("abcam ab108629", "ab108629"),
                   ("Santa Cruz sc-398486", "sc-398486"), ("CST #5174s", "5174s"), ("CST 9145", "9145")):
        sql = generate_bio_sql(q)
        assert f"antibody_catalog_number ILIKE '%{cat}%'" in sql, q
        assert "%sc-%" not in sql, q          # no stray fragment AND'd in
        _guarded(q)
    assert "antibody_catalog_number ILIKE '%sc-398486%'" in generate_bio_sql("sc-398486")   # term column


def test_cell_line_is_not_a_site_and_greek_letters_survive():
    assert "residue" not in generate_bio_sql("T24 STAT3") and "%T24%" in generate_bio_sql("T24 STAT3")
    assert "residue ILIKE 'Thr' AND residue_position = 389" in generate_bio_sql("S6K T389")
    sql = generate_bio_sql("IκBα")
    assert "iκbα" in sql.lower() and "'%ib%'" not in sql and "%ib(" not in sql   # was the term "ib"
    _guarded("IκBα")
    assert "%expression%" not in generate_bio_sql("STAT3 expression")


def test_coip():
    sql = generate_bio_sql("co-IP EGFR")
    assert "experiment_type ILIKE 'co_ip'" in sql
    assert "%egfr([^a-z]%)?" in sql
    _guarded("co-IP EGFR")


def test_cell_line_and_protein_terms_are_anded():
    sql = generate_bio_sql("A549 STAT3")
    # Two independent term groups, AND'd; each ORs across the bio columns.
    assert sql.count("cell_line ILIKE") == 2
    assert " AND " in sql


def test_loading_control_and_needs_review():
    sql = generate_bio_sql("loading control needs review")
    assert "experiment_type ILIKE 'loading_control'" in sql
    assert "needs_review = true" in sql


def test_stopwords_dropped():
    sql = generate_bio_sql("show me western blot evidence for STAT3 in cells")
    assert "%STAT3%" in sql
    for w in ("western", "blot", "evidence", "cells"):
        assert f"%{w}%" not in sql.lower()


def test_empty_query_is_a_plain_select():
    sql = generate_bio_sql("   ")
    assert sql.strip().upper().startswith("SELECT * FROM")
    assert "WHERE" not in sql.upper()
    _guarded("   ")


def test_injection_attempt_is_neutralized():
    hostile = "STAT3'; DROP TABLE western_blot_records; --"
    sql = generate_bio_sql(hostile)
    # The hostile text is demoted to harmless ILIKE search literals: the result
    # is exactly one plain SELECT, with no Drop/Command nodes anywhere, and it
    # still passes the guard. ("DROP" MAY appear inside a quoted '%DROP%'
    # literal — that is a search term, not a statement.)
    stmts = sqlglot.parse(sql, read="postgres")
    assert len(stmts) == 1 and isinstance(stmts[0], exp.Select)
    assert not list(stmts[0].find_all(exp.Drop, exp.Command))
    guarded = guard_and_limit_sql(sql, 10)
    assert isinstance(sqlglot.parse_one(guarded, read="postgres"), exp.Select)


def test_settled_evidence_ordered_first():
    assert "ORDER BY needs_review ASC" in generate_bio_sql("STAT3")


def test_p_prefix_term_does_not_add_phospho_filter():
    # Regression: "P-ERK" used to add modification_type ILIKE '%phospho%',
    # which EXCLUDED the P-ERK rows whose modification is honestly
    # CONFLICTING (null scalar). The prefix term matches the printed label;
    # no modification filter may be inferred from it.
    sql = generate_bio_sql("needs review P-ERK")
    assert "modification_type" not in sql
    assert "%P-ERK%" in sql and "needs_review = true" in sql
    _guarded("needs review P-ERK")


def test_phospho_word_filter_includes_unsettled():
    # An explicit phospho search must SURFACE disputed phospho-vs-total rows
    # (status CONFLICTING/AMBIGUOUS), not hide them behind the null scalar.
    sql = generate_bio_sql("phospho ERK")
    assert "modification_type ILIKE '%phospho%'" in sql
    assert "CONFLICTING" in sql and "AMBIGUOUS" in sql
    _guarded("phospho ERK")


def test_short_gene_symbol_does_not_match_inside_a_word():
    # Regression: '%MYC%' matched Rapamycin / Bafilomycin treatments, so a MYC
    # search on the local corpus returned 90 rows of which 4 were MYC.
    sql = generate_bio_sql("MYC 10.3892/br.2026.2108")
    assert "lower(treatment_name) SIMILAR TO '%myc([^a-z]%)?'" in sql
    assert "treatment_name ILIKE '%MYC%'" not in sql
    assert "lower(doi) = '10.3892/br.2026.2108'" in sql
    assert "target ILIKE '%STAT3%'" in generate_bio_sql("STAT3")   # longer terms stay substring
    guarded = _guarded("MYC")
    assert "SIMILAR TO" in guarded and isinstance(sqlglot.parse_one(guarded, read="postgres"), exp.Select)


def test_pasted_doi_is_an_exact_paper_filter():
    # Regression: a DOI was split into substring terms, so '(00)' became a
    # Ser92 site filter, '_' was stripped, and a truncated DOI matched a longer one.
    sql = generate_bio_sql("10.1016/S0092-8674(00)81683-9")
    assert "lower(doi) = '10.1016/s0092-8674(00)81683-9'" in sql
    assert "residue" not in sql and "ILIKE" not in sql
    for pasted in ("https://doi.org/10.1234/ABC_def.", "doi: 10.1234/abc_def", "https://dx.doi.org/10.1234/abc_def"):
        sql = generate_bio_sql(pasted)
        assert "lower(doi) = '10.1234/abc_def'" in sql and "ILIKE" not in sql, pasted   # no leftover prefix term
    sql = generate_bio_sql("phospho STAT3 Tyr705 10.3892/br.2026.2108")
    assert "residue_position = 705" in sql and "lower(doi) = '10.3892/br.2026.2108'" in sql
    assert "lower(doi) = '10.1234/x;drop'" in generate_bio_sql("10.1234/x';DROP")   # quote cannot close the literal
    for q in ("10.1016/S0092-8674(00)81683-9", "phospho STAT3 10.3892/br.2026.2108", "10.1234/x';DROP"):
        _guarded(q)
