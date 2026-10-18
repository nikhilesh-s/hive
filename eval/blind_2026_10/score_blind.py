#!/usr/bin/env python3
"""Blind benchmark tools (PREREGISTRATION.md §6-8).

    # crops for the human mapper: images and page numbers only, no extracted values
    score_blind.py mapper-pack PRIVATE_DIR OUT_DIR
    # score the sealed outputs against the primary annotator (optionally with adjudications)
    score_blind.py score PRIVATE_DIR --annotator tanvi [--adjudications FILE]
    # agreement between two annotators on the panels both fully annotated
    score_blind.py agreement --annotator tanvi --second NAME
    # synthetic self-check of the scoring logic (no data needed)
    score_blind.py self-test

Annotation CSVs live in annotations/<annotator>/ (panels.csv, targets.csv, lanes.csv,
timelog.csv); the crop map in annotations/crop_map.csv. Formats: ANNOTATOR_GUIDE.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "model_comparison"))
from compare_records import _fstatus, _fv  # noqa: E402  (Evidence Field envelope readers)

FIELDS = ("protein_identity", "modification_type", "phospho_site", "cell_line", "treatment",
          "band_call")
CATS = ("CORRECT", "INCORRECT", "ABSTAINED", "NOT_FOUND", "CORRECT_SILENCE", "UNSUPPORTED")
SILENT = {"not_stated", "none", ""}
AA = {"tyr": "y", "ser": "s", "thr": "t", "his": "h", "lys": "k", "arg": "r", "asp": "d"}
GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "κ": "kappa", "µ": "u", "μ": "u"}


# ---------- normalization ----------
def norm(s) -> str:
    s = str(s or "").lower()
    for k, v in GREEK.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]", "", s)


def norm_cell(s) -> str:
    return norm(re.sub(r"\b(cells?|cell lines?)\b", "", str(s or ""), flags=re.I))


def alts(cell, f=norm) -> set[str]:
    """'IL-6|interleukin 6; TNF' -> every synonym of every item, normalized."""
    return {f(a) for item in str(cell or "").split(";") for a in item.split("|") if f(a)}


def silent(cell) -> bool:
    return norm(cell).replace("notstated", "not_stated") in SILENT or str(cell).strip().upper() == "NOT_STATED"


def site_key(residue, position) -> str:
    r = norm(residue)
    return f"{AA.get(r, r[:1])}{position}" if r and position not in (None, "") else ""


def annotated_mod(cell) -> tuple[str, set[str]]:
    """'phospho:T202/Y204' -> ('phospho', {'t202','y204'}); 'total' -> ('total', set())."""
    text = str(cell or "").strip()
    if text.upper() == "NOT_STATED" or not text:
        return "NOT_STATED", set()
    kind, _, sites = text.partition(":")
    kind = norm(kind) or "other"
    kind = {"phosphorylation": "phospho", "cleavage": "cleaved", "unmodified": "total"}.get(kind, kind)
    found = set()
    for s in sites.split("/"):
        m = re.match(r"\s*([A-Za-z]{1,3})\s*-?\s*(\d+)", s)
        if m:
            found.add(site_key(m.group(1), m.group(2)))
    return kind, found


# ---------- system values (asserted only when SUPPORTED) ----------
def sys_field(rec: dict, path: list[str]):
    st = _fstatus(rec, path)
    val = _fv(rec, path)
    return (val, True) if st == "SUPPORTED" and val not in (None, "", []) else (None, False)


def sys_mod(rec: dict) -> tuple[str | None, str]:
    path = ["modification", "modification_type"]
    if _fstatus(rec, path) != "SUPPORTED":
        return None, ""
    kind = _fv(rec, path)
    kind = {None: "total", "phosphorylation": "phospho", "cleavage": "cleaved"}.get(kind, "other")
    site = site_key(_fv(rec, ["modification", "residue"]), _fv(rec, ["modification", "residue_position"]))
    return kind, site


def sys_sample(rec: dict):
    val, ok = sys_field(rec, ["sample", "cell_line"])
    return (val, ok) if ok else sys_field(rec, ["sample", "sample"])


def symbols_match(system_value, annotated_cell) -> bool:
    """'MAPK1/MAPK3' vs 'MAPK3|MAPK1': every system symbol must be one the annotator listed (A3)."""
    got = {norm(s) for s in re.split(r"[/,;|]", str(system_value or "")) if norm(s)}
    return bool(got) and got <= alts(annotated_cell)


# ---------- scoring one aligned pair ----------
def judge(asserted: bool, correct: bool, annotated_silent: bool) -> str:
    if annotated_silent:
        return "UNSUPPORTED" if asserted else "CORRECT_SILENCE"
    if not asserted:
        return "ABSTAINED"
    return "CORRECT" if correct else "INCORRECT"


def score_row(row: dict, rec: dict) -> dict[str, tuple[str, str, str]]:
    """field -> (category, annotated value, system value)."""
    out = {}
    canon, ok = sys_field(rec, ["target", "canonical_target"])
    out["protein_identity"] = (judge(ok, symbols_match(canon, row["gene_symbol"]), silent(row["gene_symbol"])),
                               row["gene_symbol"], str(canon))
    a_kind, a_sites = annotated_mod(row["modification"])
    s_kind, s_site = sys_mod(rec)
    out["modification_type"] = (judge(s_kind is not None, s_kind == a_kind, a_kind == "NOT_STATED"),
                                row["modification"], f"{s_kind} {s_site}".strip())
    if a_kind == "phospho" and a_sites:
        out["phospho_site"] = (judge(bool(s_site), s_site in a_sites, False), row["modification"], s_site)
    sample, ok = sys_sample(rec)
    out["cell_line"] = (judge(ok, norm_cell(sample) in alts(row["cell_line_or_sample"], norm_cell),
                              silent(row["cell_line_or_sample"])), row["cell_line_or_sample"], str(sample))
    treat, ok = sys_field(rec, ["treatment", "treatment_name"])
    out["treatment"] = (judge(ok, norm(treat) in alts(row["treatments"]), silent(row["treatments"])),
                        row["treatments"], str(treat))
    return out


def score_lanes(lanes: list[dict], rec: dict | None) -> list[tuple[int, str, str, str]]:
    """[(lane_index, category, annotated, system)] for lanes the annotator called present/absent."""
    sys_lanes = {}
    for b in (rec or {}).get("bands") or []:
        val, ok = sys_field(b, ["band_state"])
        sys_lanes[int(b.get("lane_index") or 0)] = val if ok and val in ("present", "absent") else None
    out = []
    for lane in lanes:
        call = lane["band_call"].strip().lower()
        if call not in ("present", "absent"):
            continue
        idx = int(lane["lane_index"])
        if rec is None or idx not in sys_lanes:
            out.append((idx, "NOT_FOUND", call, ""))
        elif sys_lanes[idx] is None:
            out.append((idx, "ABSTAINED", call, "uncertain"))
        else:
            out.append((idx, "CORRECT" if sys_lanes[idx] == call else "INCORRECT", call, sys_lanes[idx]))
    return out


# ---------- data loading ----------
def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]


def frozen_papers() -> list[dict]:
    return [p for p in json.loads((HERE / "papers.json").read_text())["papers"] if p["status"] == "frozen"]


def fig_key(figure, letter) -> tuple[str, str]:
    num = re.search(r"\d+", str(figure or ""))
    return (num.group(0) if num else norm(figure), norm(letter))


def crop_panels(cmap_rows: list[dict], inventory: list[dict]) -> dict[str, list[str] | str]:
    """crop file -> inventory panel ids, or 'NOT_WB' / 'WB_NOT_IN_INVENTORY'.
    The mapper writes figure + panel letters (e.g. figure 2, panels 'A;B'); joined on the inventory."""
    by_fig = defaultdict(list)
    for p in inventory:
        by_fig[fig_key(p["figure"], p["panel_letter"])].append(p["panel_id"])
    out: dict[str, list[str] | str] = {}
    for r in cmap_rows:
        mapping = r["mapping"].strip().upper()
        if mapping in ("NOT_WB", "WB_NOT_IN_INVENTORY"):
            out[r["crop_file"]] = mapping
            continue
        ids = []
        for letter in (r["panel_letters"].split(";") if r["panel_letters"] else [""]):
            ids += by_fig.get(fig_key(r["figure"], letter), [])
        out[r["crop_file"]] = sorted(set(ids)) or "WB_NOT_IN_INVENTORY"
    return out


# ---------- scoring a paper ----------
def score_paper(inventory, targets, lanes, cmap_rows, records) -> dict:
    inv_ids = [p["panel_id"] for p in inventory]
    sampled = {t["panel_id"] for t in targets}
    cmap = crop_panels(cmap_rows, inventory)
    placed: list[tuple[dict, set]] = []   # (record, inventory panel ids its crop covers)
    counts = Counter()
    for rec in records:
        crop = Path(str((rec.get("figure") or {}).get("image_crop_ref") or "")).name
        m = cmap.get(crop)
        if m is None:
            counts["records_unmapped"] += 1
        elif m == "NOT_WB":
            counts["spurious_records_not_wb"] += 1
        elif m == "WB_NOT_IN_INVENTORY":
            counts["records_on_panels_missing_from_inventory"] += 1
        else:
            placed.append((rec, set(m)))
    found = {pid for _, ps in placed for pid in ps}
    fields = {f: Counter() for f in FIELDS}
    cells = []
    lanes_by_row = defaultdict(list)
    for lane in lanes:
        lanes_by_row[(lane["panel_id"], lane["row_order"])].append(lane)
    rows_by_panel = defaultdict(list)
    for t in targets:
        rows_by_panel[t["panel_id"]].append(t)

    def note(field, cat, row, a, s, lane=""):
        fields[field][cat] += 1
        if cat in ("INCORRECT", "UNSUPPORTED"):
            cells.append({"panel_id": row["panel_id"], "row_order": row["row_order"],
                          "target_printed": row["target_printed"], "field": field,
                          "lane_index": lane, "annotated": a, "system": s, "verdict": ""})

    def printed(r, row):
        return norm(r["target"].get("raw_target_name")) == norm(row["target_printed"])

    def symbol(r, row):
        return symbols_match(sys_field(r, ["target", "canonical_target"])[0], row["gene_symbol"])

    def same_mod(r, row):
        kind, sites = annotated_mod(row["modification"])
        s_kind, s_site = sys_mod(r)
        return s_kind == kind and (not sites or s_site in sites)

    used: set[int] = set()
    for pid in sorted(sampled, key=lambda x: int(x)):
        pool = [r for r, ps in placed if pid in ps]   # every crop that covers this panel (A3)
        aligned = {}
        # pass 1: printed label for every row; pass 2: gene symbol, preferring the same modification (A3)
        for row in rows_by_panel[pid]:
            r = next((r for r in pool if id(r) not in used and printed(r, row)), None)
            if r is not None:
                used.add(id(r)); aligned[row["row_order"]] = r
        for row in rows_by_panel[pid]:
            if row["row_order"] in aligned:
                continue
            cands = [r for r in pool if id(r) not in used and symbol(r, row)]
            r = next((c for c in cands if same_mod(c, row)), cands[0] if cands else None)
            if r is not None:
                used.add(id(r)); aligned[row["row_order"]] = r
        for row in rows_by_panel[pid]:
            rec = aligned.get(row["row_order"])
            if rec is None:
                for field in FIELDS[:-1]:
                    if field == "phospho_site" and not annotated_mod(row["modification"])[1]:
                        continue
                    col = {"protein_identity": "gene_symbol", "modification_type": "modification",
                           "phospho_site": "modification", "cell_line": "cell_line_or_sample",
                           "treatment": "treatments"}[field]
                    if field == "modification_type" and annotated_mod(row[col])[0] == "NOT_STATED":
                        continue
                    if field != "modification_type" and silent(row[col]):
                        continue
                    fields[field]["NOT_FOUND"] += 1
            else:
                for field, (cat, a, s_) in score_row(row, rec).items():
                    note(field, cat, row, a, s_)
            for idx, cat, a, s_ in score_lanes(lanes_by_row[(pid, row["row_order"])], rec):
                note("band_call", cat, row, a, s_, lane=str(idx))
    for r, ps in placed:   # leftovers on fully annotated panels
        if id(r) in used or not ps <= sampled:
            continue
        rows = [row for pid in ps for row in rows_by_panel[pid]]
        if any(printed(r, row) or symbol(r, row) for row in rows):
            counts["duplicate_records"] += 1   # same target again from an overlapping crop (A3)
        else:
            counts["spurious_records_unaligned"] += 1
    wrong = sum(fields[f]["INCORRECT"] + fields[f]["UNSUPPORTED"] for f in FIELDS)
    return {
        "panels_inventoried": len(inv_ids),
        "panels_found": len(found & set(inv_ids)),
        "panels_fully_annotated": len(sampled),
        "target_rows_annotated": len(targets),
        "records": len(records),
        **counts,
        "incorrect_assertions": wrong + counts["spurious_records_not_wb"] + counts["spurious_records_unaligned"],
        "fields": {f: dict(c) for f, c in fields.items()},
        "cells_to_adjudicate": cells,
    }


def apply_adjudication(rep: dict, verdicts: dict) -> dict:
    """EQUIVALENT_NOTATION turns an INCORRECT/UNSUPPORTED cell into CORRECT/CORRECT_SILENCE."""
    adj = {f: Counter(c) for f, c in rep["fields"].items()}
    for c in rep["cells_to_adjudicate"]:
        key = (c["panel_id"], c["row_order"], c["field"], c["lane_index"])
        if verdicts.get(key) == "EQUIVALENT_NOTATION":
            was = "INCORRECT" if adj[c["field"]]["INCORRECT"] and c["annotated"] and not silent(c["annotated"]) else "UNSUPPORTED"
            adj[c["field"]][was] -= 1
            adj[c["field"]]["CORRECT" if was == "INCORRECT" else "CORRECT_SILENCE"] += 1
    return {f: dict(c) for f, c in adj.items()}


def metrics(c: dict) -> dict:
    g = Counter(c)
    n = g["CORRECT"] + g["INCORRECT"] + g["ABSTAINED"] + g["NOT_FOUND"]
    asserted = g["CORRECT"] + g["INCORRECT"] + g["UNSUPPORTED"]
    frac = lambda a, b: f"{a}/{b} ({a / b:.0%})" if b else "n/a (0)"
    return {"accuracy": frac(g["CORRECT"], n), "precision_of_assertions": frac(g["CORRECT"], asserted),
            "abstained": frac(g["ABSTAINED"], n), "not_found": frac(g["NOT_FOUND"], n),
            "unsupported_assertions": g["UNSUPPORTED"], **{k: g[k] for k in CATS}}


# ---------- commands ----------
def cmd_mapper_pack(private: Path, out: Path) -> None:
    rows = []
    for p in frozen_papers():
        run = private / "runs" / p["pmcid"]
        dest = out / p["pmcid"]
        dest.mkdir(parents=True, exist_ok=True)
        for c in json.loads((run / "llm_candidates.json").read_text()):
            src = Path(c["candidate_path"])
            src = src if src.is_absolute() else run / "panel_candidates" / src.name
            shutil.copyfile(src, dest / src.name)
            rows.append({"paper_pmcid": p["pmcid"], "crop_file": src.name, "page": c.get("page", ""),
                         "figure": "", "panel_letters": "", "mapping": "", "mapper_note": ""})
    with (out / "crop_map.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "crops ->", out)


def verify_seal(private: Path) -> str:
    bad = []
    for line in (HERE / "SEALED_OUTPUTS.sha256").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        f = private / rel
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            bad.append(rel)
    if bad:
        raise SystemExit(f"sealed outputs changed or missing: {bad[:5]}")
    return "all sealed files match SEALED_OUTPUTS.sha256"


def cmd_score(private: Path, annotator: str, adjudications: Path | None) -> None:
    seal = verify_seal(private)
    code = subprocess.run(["git", "diff", "--stat", "f77d311", "--", "western_blot_miner", "api"],
                          cwd=HERE.parents[1], capture_output=True, text=True).stdout.strip()
    ann = HERE / "annotations" / annotator
    inv, tg, ln, tl = (read_csv(ann / f"{n}.csv") for n in ("panels", "targets", "lanes", "timelog"))
    cmap = read_csv(HERE / "annotations" / "crop_map.csv")
    verdicts = {(r["paper_pmcid"], r["panel_id"], r["row_order"], r["field"], r["lane_index"]): r["verdict"].strip().upper()
                for r in read_csv(adjudications)} if adjudications else {}
    papers, pooled_raw, pooled_adj, cells = {}, defaultdict(Counter), defaultdict(Counter), []
    totals = Counter()
    for p in frozen_papers():
        pick = lambda rows: [r for r in rows if r["paper_pmcid"] == p["pmcid"]]
        rec_path = private / "runs" / p["pmcid"] / "evidence_records.json"
        records = json.loads(rec_path.read_text()) if rec_path.exists() else []
        rep = score_paper(pick(inv), pick(tg), pick(ln), pick(cmap), records)
        mine = {k[1:]: v for k, v in verdicts.items() if k[0] == p["pmcid"]}   # panel ids restart per paper
        adj = apply_adjudication(rep, mine) if mine else rep["fields"]
        timing = json.loads((private / "runs" / p["pmcid"] / "timing.json").read_text())
        manual = Counter()
        for r in pick(tl):
            manual[r["task"]] += float(r["minutes"] or 0)
        rep["timing"] = {"automated_seconds": round(timing.get("preprocess_seconds", 0) + timing.get("extract_seconds", 0), 1),
                         "panels_sent_to_model": timing.get("panels_queried"),
                         "manual_minutes": dict(manual)}
        for c in rep.pop("cells_to_adjudicate"):
            cells.append({"paper_pmcid": p["pmcid"], **c})
        for f in FIELDS:
            pooled_raw[f].update(rep["fields"][f])
            pooled_adj[f].update(adj[f])
        for k in ("panels_inventoried", "panels_found", "panels_fully_annotated", "target_rows_annotated",
                  "records", "incorrect_assertions", "spurious_records_not_wb", "spurious_records_unaligned",
                  "records_on_panels_missing_from_inventory", "records_unmapped", "duplicate_records"):
            totals[k] += rep.get(k, 0)
        totals["automated_seconds"] += rep["timing"]["automated_seconds"]
        totals["panels_sent_to_model"] += rep["timing"]["panels_sent_to_model"] or 0
        totals["manual_full_minutes"] += manual.get("full", 0)
        rep["metrics_raw"] = {f: metrics(rep["fields"][f]) for f in FIELDS}
        rep["metrics_adjudicated"] = {f: metrics(adj[f]) for f in FIELDS}
        papers[p["pmcid"]] = rep
    out = HERE / "report"
    out.mkdir(exist_ok=True)
    result = {"annotator": annotator, "seal_check": seal,
              "frozen_code_diff_vs_f77d311": code or "none",
              "papers": papers, "pooled": dict(totals),
              "pooled_metrics_raw": {f: metrics(pooled_raw[f]) for f in FIELDS},
              "pooled_metrics_adjudicated": {f: metrics(pooled_adj[f]) for f in FIELDS},
              "adjudicated": bool(verdicts)}
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (out / "adjudication_sheet.csv").open("w", newline="") as f:
        cols = ["paper_pmcid", "panel_id", "row_order", "target_printed", "field", "lane_index",
                "annotated", "system", "verdict"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(cells)
    (out / "RESULTS.md").write_text(render(result))
    print((out / "RESULTS.md").read_text())


def render(r: dict) -> str:
    t = r["pooled"]
    pr = lambda a, b: f"{a}/{b} ({a / b:.0%})" if b else "n/a"
    lines = ["# Blind benchmark results (generated by score_blind.py; do not edit by hand)", "",
             f"- Papers: {len(r['papers'])}. Annotator: {r['annotator']}. Adjudicated: {r['adjudicated']}.",
             f"- Integrity: {r['seal_check']}. System code diff vs f77d311: {r['frozen_code_diff_vs_f77d311']}.",
             f"- Panel recall (all inventoried Western-blot panels): {pr(t['panels_found'], t['panels_inventoried'])}.",
             f"- Fully annotated: {t['panels_fully_annotated']} panels, {t['target_rows_annotated']} target rows.",
             f"- Incorrect assertions (wrong values + unsupported values + spurious records): {t['incorrect_assertions']}"
             f" (spurious: {t['spurious_records_not_wb']} on non-Western crops, {t['spurious_records_unaligned']} unaligned).",
             f"- Records on panels missing from the inventory (not counted against the system): "
             f"{t['records_on_panels_missing_from_inventory']}. Unmapped records: {t['records_unmapped']}. "
             f"Duplicate records from overlapping crops (not scored, not counted as errors): {t['duplicate_records']}.",
             f"- Automated time: {t['automated_seconds'] / 60:.1f} min for {t['panels_sent_to_model']} panels sent to the model."
             f" Manual full annotation: {t['manual_full_minutes']:.0f} min for {t['panels_fully_annotated']} panels.",
             "", "This is 4 papers drawn from a deliberately diverse candidate pool. It is not a literature-wide accuracy figure.", ""]
    for label, key in (("Raw", "pooled_metrics_raw"), ("Adjudicated", "pooled_metrics_adjudicated")):
        lines += [f"## Pooled, {label.lower()}", "",
                  "| Field | Accuracy | Precision of assertions | Abstained | Not found | Unsupported |",
                  "|---|---|---|---|---|---|"]
        for f, m in r[key].items():
            lines.append(f"| {f} | {m['accuracy']} | {m['precision_of_assertions']} | {m['abstained']} | "
                         f"{m['not_found']} | {m['unsupported_assertions']} |")
        lines.append("")
    lines += ["## Per paper (raw)", ""]
    for pmcid, p in r["papers"].items():
        lines.append(f"### {pmcid}: panel recall {pr(p['panels_found'], p['panels_inventoried'])}, "
                     f"{p['records']} records, {p['incorrect_assertions']} incorrect assertions, "
                     f"automated {p['timing']['automated_seconds']} s, manual {p['timing']['manual_minutes']}")
        lines.append("")
        lines.append("| Field | Accuracy | Precision | Abstained | Not found |")
        lines.append("|---|---|---|---|---|")
        for f, m in p["metrics_raw"].items():
            lines.append(f"| {f} | {m['accuracy']} | {m['precision_of_assertions']} | {m['abstained']} | {m['not_found']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def cmd_agreement(a: str, b: str) -> None:
    load = lambda who, n: read_csv(HERE / "annotations" / who / f"{n}.csv")
    key = lambda t: (t["paper_pmcid"], t["panel_id"], tuple(sorted(alts(t["gene_symbol"]))))
    ta, tb = {key(t): t for t in load(a, "targets")}, {key(t): t for t in load(b, "targets")}
    agree = Counter()
    for k in ta.keys() & tb.keys():
        x, y = ta[k], tb[k]
        for col, f in (("modification", lambda v: annotated_mod(v)), ("cell_line_or_sample", lambda v: alts(v, norm_cell)),
                       ("treatments", alts)):
            agree[(col, f(x[col]) == f(y[col]))] += 1
    la = {(l["paper_pmcid"], l["panel_id"], l["row_order"], l["lane_index"]): l["band_call"].lower() for l in load(a, "lanes")}
    lb = {(l["paper_pmcid"], l["panel_id"], l["row_order"], l["lane_index"]): l["band_call"].lower() for l in load(b, "lanes")}
    for k in la.keys() & lb.keys():
        agree[("band_call", la[k] == lb[k])] += 1
    print(f"target rows in both: {len(ta.keys() & tb.keys())} (A only {len(ta.keys() - tb.keys())}, B only {len(tb.keys() - ta.keys())})")
    for col in ("modification", "cell_line_or_sample", "treatments", "band_call"):
        n = agree[(col, True)] + agree[(col, False)]
        print(f"{col}: {agree[(col, True)]}/{n} agree" if n else f"{col}: n/a")


def self_test() -> None:
    def field(v, st="SUPPORTED"):
        return {"value": v, "status": st}

    def rec(raw, canon, cell, treat, mod=None, residue=None, pos=None, crop="c1.png", bands=()):
        return {"figure": {"image_crop_ref": f"/x/{crop}"},
                "target": {"raw_target_name": raw, "canonical_target": field(canon, "SUPPORTED" if canon else "MISSING")},
                "modification": {"modification_type": field(mod), "residue": field(residue), "residue_position": field(pos)},
                "sample": {"cell_line": field(cell, "SUPPORTED" if cell else "MISSING"), "sample": field(None, "MISSING")},
                "treatment": {"treatment_name": field(treat, "SUPPORTED" if treat else "MISSING")},
                "bands": [{"lane_index": i + 1, "band_state": field(s, "SUPPORTED")} for i, s in enumerate(bands)]}

    inv = [{"panel_id": "1", "figure": "1", "panel_letter": "A"}, {"panel_id": "2", "figure": "1", "panel_letter": "B"},
           {"panel_id": "3", "figure": "2", "panel_letter": "A"}]
    tg = [{"panel_id": "1", "row_order": "1", "target_printed": "p-STAT3 (Y705)", "gene_symbol": "STAT3",
           "modification": "phospho:Y705", "cell_line_or_sample": "Hep3B", "treatments": "IL-6|interleukin 6"},
          {"panel_id": "1", "row_order": "2", "target_printed": "GAPDH", "gene_symbol": "GAPDH",
           "modification": "total", "cell_line_or_sample": "Hep3B", "treatments": "IL-6"},
          {"panel_id": "3", "row_order": "1", "target_printed": "Bax", "gene_symbol": "BAX",
           "modification": "total", "cell_line_or_sample": "HCT116", "treatments": "NOT_STATED"}]
    ln = [{"panel_id": "1", "row_order": "1", "lane_index": str(i), "band_call": c}
          for i, c in ((1, "absent"), (2, "present"), (3, "uncertain"))]
    cmap = [{"crop_file": "c1.png", "figure": "Fig 1", "panel_letters": "A;B", "mapping": ""},
            {"crop_file": "c9.png", "figure": "", "panel_letters": "", "mapping": "NOT_WB"}]
    recs = [rec("P-STAT3 (Tyr705)", "STAT3", "Hep3B cells", "IL-6", "phosphorylation", "Tyr", 705,
                bands=("absent", "absent", "present")),
            rec("GAPDH", "GAPDH", "HepG2", None),
            rec("Ki67", "MKI67", None, "IL-6", crop="c9.png")]
    tg.append({"panel_id": "2", "row_order": "1", "target_printed": "P-ERK 1/2", "gene_symbol": "MAPK3|MAPK1",
               "modification": "phospho", "cell_line_or_sample": "Hep3B", "treatments": "IL-6"})
    cmap.append({"crop_file": "c2.png", "figure": "1", "panel_letters": "B", "mapping": ""})
    cmap.append({"crop_file": "c3.png", "figure": "1", "panel_letters": "B", "mapping": ""})
    recs.append(rec("P-ERK 1/2", "MAPK1/MAPK3", "Hep3B", "IL-6", "phosphorylation", crop="c2.png"))   # 2nd crop of panel 2
    recs.append(rec("P-ERK 1/2", "MAPK1/MAPK3", "Hep3B", "IL-6", "phosphorylation", crop="c3.png"))   # overlapping duplicate
    # misread label on panel 3: two STAT3 records, the Ser727 one listed first; the Y705 row must take the Y705 record
    tg.append({"panel_id": "3", "row_order": "2", "target_printed": "pSTAT3 Y705", "gene_symbol": "STAT3",
               "modification": "phospho:Y705", "cell_line_or_sample": "HCT116", "treatments": "none"})
    cmap.append({"crop_file": "c4.png", "figure": "2", "panel_letters": "A", "mapping": ""})
    recs.append(rec("p-STAT3 S727", "STAT3", "HCT116", None, "phosphorylation", "Ser", 727, crop="c4.png"))
    recs.append(rec("p-STAT3 Y-705", "STAT3", "HCT116", None, "phosphorylation", "Tyr", 705, crop="c4.png"))
    r = score_paper(inv, tg, ln, cmap, recs)
    f = r["fields"]
    assert (r["panels_inventoried"], r["panels_found"]) == (3, 3), r          # c4 covers panel 3
    assert f["protein_identity"] == {"CORRECT": 4, "NOT_FOUND": 1}, f            # MAPK1/MAPK3 == MAPK3|MAPK1
    assert r["duplicate_records"] == 2 and r.get("spurious_records_unaligned", 0) == 0, r   # + leftover S727
    assert f["phospho_site"] == {"CORRECT": 2}, f                                  # Y705 row got the Y705 record
    assert f["modification_type"] == {"CORRECT": 4, "NOT_FOUND": 1}, f
    assert f["cell_line"] == {"CORRECT": 3, "INCORRECT": 1, "NOT_FOUND": 1}, f    # 'Hep3B cells' == 'Hep3B'
    assert f["treatment"] == {"CORRECT": 2, "ABSTAINED": 1, "CORRECT_SILENCE": 1}, f                    # Bax: NOT_STATED, not found -> unscored
    assert f["band_call"] == {"CORRECT": 1, "INCORRECT": 1}, f                    # lane 3 annotator-uncertain: unscored
    assert r["spurious_records_not_wb"] == 1 and r["incorrect_assertions"] == 3, r
    adj = apply_adjudication(r, {("1", "2", "cell_line", ""): "EQUIVALENT_NOTATION"})
    assert adj["cell_line"] == {"CORRECT": 4, "INCORRECT": 0, "NOT_FOUND": 1}, adj
    assert metrics(f["protein_identity"])["accuracy"] == "4/5 (80%)"
    print("self-test passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mapper-pack"); m.add_argument("private", type=Path); m.add_argument("out", type=Path)
    s = sub.add_parser("score"); s.add_argument("private", type=Path); s.add_argument("--annotator", required=True)
    s.add_argument("--adjudications", type=Path)
    g = sub.add_parser("agreement"); g.add_argument("--annotator", required=True); g.add_argument("--second", required=True)
    sub.add_parser("self-test")
    a = ap.parse_args()
    if a.cmd == "mapper-pack":
        cmd_mapper_pack(a.private, a.out)
    elif a.cmd == "score":
        cmd_score(a.private, a.annotator, a.adjudications)
    elif a.cmd == "agreement":
        cmd_agreement(a.annotator, a.second)
    else:
        self_test()
