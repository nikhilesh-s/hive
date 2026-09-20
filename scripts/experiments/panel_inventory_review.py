"""B-4 — panel inventory scaffold and CV-detector review list.

What this does WITHOUT ground truth (safe to run any time):
  * per paper, per page: stored candidates (candidates.json only keeps crops
    that passed the 0.35 crop gate), candidates actually sent to the model
    (llm_candidates.json), and whether the page text mentions a western /
    immunoblot;
  * a review list of candidates that were NOT sent to the model on pages whose
    text mentions a western blot -- the places a real panel may have been
    dropped (recorded issue M10);
  * a blank `eval/demo/<paper>/panel_inventory.json` per reviewed paper if one
    does not exist yet, for a human (Tanvi) to fill with the real per-page
    western panel count, targets and lane counts.

What it does only once a human has filled an inventory (`"status": "filled"`):
  * page-level recall proxy = sum over pages of min(sent, panels) / panels,
    and precision proxy = sum of min(sent, panels) / sent. These are COUNT
    proxies (no per-panel box matching) and are labelled as such.

Thresholds are reported, never changed here (ticket B-4 forbids it).

Run: .venv/bin/python scripts/experiments/panel_inventory_review.py
Writes research/experiments/B4_panel_inventory_review.md (+ templates).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "western_blot_miner" / "data" / "pdf_runs"
OUT = ROOT / "research" / "experiments" / "B4_panel_inventory_review.md"

# reviewed papers: pdf run dir -> eval/demo dir
REVIEWED = {
    "10.3892_br.2026.2108": "phospho_PMC12856536",
    "10.3892_ijmm.2022.5188": "standard_PMC9559174",
    "10.1186_s12964-025-02385-8": "coip_PMC12706926",
}
CROP_GATE = 0.35
BLOT_WORDS = re.compile(r"western\s*blot|immunoblot|\bWB\b", re.IGNORECASE)


def load(run: Path):
    cands = json.loads((run / "candidates.json").read_text())
    sent = {c["candidate_path"] for c in json.loads((run / "llm_candidates.json").read_text())}
    pages = {p["page"]: p.get("text", "") for p in json.loads((run / "pages.json").read_text())}
    return cands, sent, pages


def template(paper_id: str, pages: dict[int, str]) -> dict:
    return {
        "paper_id": paper_id,
        "status": "unfilled",
        "filled_by": None,
        "instructions": ("For every page, count the western blot panels a biologist would extract (one entry "
                         "per panel). Do not copy anything from HiveBlot output. Leave pages without westerns "
                         "as an empty list. Set status to 'filled' when done."),
        "pages": {str(p): [] for p in sorted(pages)},
        "panel_entry_example": {"figure": "Fig 2C", "targets": ["LC3B", "ACTB"], "lanes": 6},
    }


def main() -> int:
    lines = ["# B-4 — panel inventory scaffold and CV-detector review list", "",
             "`scripts/experiments/panel_inventory_review.py`. Detector counts and a review list need no ground "
             "truth. Recall / precision need a human-filled `eval/demo/<paper>/panel_inventory.json`; until then "
             "they are reported as blocked, never estimated. Thresholds are reported, not changed.", "",
             f"Limitation: `candidates.json` only stores crops that already passed the crop gate ({CROP_GATE}), so "
             "candidates rejected below it are not visible here. The review list covers panels lost between the "
             "crop gate and the model gate; a panel the detector scored below the crop gate (recorded issue M10) "
             "can only be found by the human inventory. Re-running preprocessing with the gate lowered would "
             "expose them and is deliberately not done here.", ""]
    for run_name, demo_name in REVIEWED.items():
        run = RUNS / run_name
        if not (run / "candidates.json").is_file():
            lines += [f"## {run_name}", "", "run directory missing; skipped", ""]
            continue
        cands, sent, pages = load(run)
        inv_path = ROOT / "eval" / "demo" / demo_name / "panel_inventory.json"
        if not inv_path.exists():
            inv_path.write_text(json.dumps(template(run_name.replace("_", "/", 1), pages), indent=1) + "\n")
        inventory = json.loads(inv_path.read_text())

        by_page: dict[int, list] = {}
        for c in cands:
            by_page.setdefault(c["page"], []).append(c)
        lines += [f"## {run_name}", "",
                  f"{len(cands)} stored candidates (all passed the crop gate {CROP_GATE}), {len(sent)} sent to the model. Inventory: `{inv_path.relative_to(ROOT)}` "
                  f"(status: {inventory.get('status')}).", "",
                  "| page | mentions western | stored candidates | sent to model | human panel count |",
                  "|---|---|---|---|---|"]
        review, hits, n_sent_total, n_panels_total = [], 0, 0, 0
        filled = inventory.get("status") == "filled"
        for page in sorted(set(pages) | set(by_page)):
            cs = by_page.get(page, [])
            blot = bool(BLOT_WORDS.search(pages.get(page, "")))
            n_sent = sum(c["candidate_path"] in sent for c in cs)
            panels = inventory.get("pages", {}).get(str(page))
            n_panels = len(panels) if isinstance(panels, list) else None
            lines.append(f"| {page} | {'yes' if blot else 'no'} | {len(cs)} | {n_sent} | "
                         f"{n_panels if filled else 'not filled'} |")
            if blot:
                review += [c for c in cs if c["candidate_path"] not in sent]
            if filled and n_panels:
                hits += min(n_sent, n_panels)
                n_panels_total += n_panels
            if filled:
                n_sent_total += n_sent
        lines.append("")
        if filled and n_panels_total:
            lines.append(f"Page-level COUNT proxies (no per-panel matching): recall {hits}/{n_panels_total} = "
                         f"{hits / n_panels_total:.2f}; precision {hits}/{n_sent_total} = "
                         f"{(hits / n_sent_total) if n_sent_total else 0:.2f}.")
        else:
            lines.append("Recall / precision: **blocked** until a human fills the inventory.")
        lines += ["", f"Review list: {len(review)} candidates on western-mentioning pages that were not sent to "
                  "the model (highest score first; check each crop for a missed panel).", ""]
        for c in sorted(review, key=lambda c: -c["cv_score"])[:25]:
            lines.append(f"- page {c['page']} · score {c['cv_score']:.2f} · `{Path(c['candidate_path']).name}`")
        if len(review) > 25:
            lines.append(f"- ... {len(review) - 25} more below score {sorted(review, key=lambda c: -c['cv_score'])[25]['cv_score']:.2f}")
        lines.append("")
    OUT.write_text("\n".join(lines).rstrip("\n") + "\n")
    print("\n".join(l for l in lines if l.startswith("## ") or "sent to the model" in l or "blocked" in l or "proxies" in l))
    return 0


if __name__ == "__main__":
    sys.exit(main())
