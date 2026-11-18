#!/usr/bin/env python3
"""Pull the team's Google Sheets into annotations/ as CSV (RUNBOOK.md step 5).

    fetch_annotations.py status     # row counts only, no cell contents printed
    fetch_annotations.py pull       # write annotations/tanvi/*.csv and annotations/crop_map.csv

Needs a Google OAuth credentials JSON; set HIVE_GOOGLE_CREDS to its path (read-only use).
Sheet IDs are the ones created on 2026-10-18.
"""
import csv
import json
import os
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
CREDS = Path(os.environ["HIVE_GOOGLE_CREDS"]) if "HIVE_GOOGLE_CREDS" in os.environ else None
TANVI_SHEET = "141LXCeDxG2UtvR7smYn6CUkHCuKRYSCIM72ZGY9nqIU"
CROP_SHEET = "1SDaLkJo4DkYc7mMoP-Yae3x8I4V_dgsPj31oG0bdqes"
TANVI_TABS = ("panels", "targets", "lanes", "timelog", "ERRATA")


def token() -> str:
    if CREDS is None:
        sys.exit("set HIVE_GOOGLE_CREDS to your Google OAuth credentials JSON")
    c = json.loads(CREDS.read_text())
    r = requests.post(c.get("token_uri") or "https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"], "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def values(tok: str, sheet: str, rng: str) -> list[list[str]]:
    r = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet}/values/{requests.utils.quote(rng)}",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    r.raise_for_status()
    return r.json().get("values", [])


def first_tab(tok: str, sheet: str) -> str:
    r = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet}?fields=sheets.properties.title",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    r.raise_for_status()
    return r.json()["sheets"][0]["properties"]["title"]


def write(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = len(rows[0]) if rows else 0
    with path.open("w", newline="") as f:
        csv.writer(f).writerows([r + [""] * (width - len(r)) for r in rows])


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    tok = token()
    crop_rows = values(tok, CROP_SHEET, first_tab(tok, CROP_SHEET))
    hdr = crop_rows[0] if crop_rows else []
    filled = sum(1 for r in crop_rows[1:] if len(r) > hdr.index("mapping") and (r[hdr.index("mapping")] or
                 (len(r) > hdr.index("figure") and r[hdr.index("figure")]))) if hdr else 0
    print(f"crop_map: {filled}/{max(len(crop_rows) - 1, 0)} crops mapped")
    tanvi = {t: values(tok, TANVI_SHEET, t) for t in TANVI_TABS}
    for t, rows in tanvi.items():
        papers = sorted({r[0] for r in rows[1:] if r})
        print(f"tanvi/{t}: {max(len(rows) - 1, 0)} rows, papers {papers}")
    if mode == "pull":
        write(HERE / "annotations/crop_map.csv", crop_rows)
        for t, rows in tanvi.items():
            write(HERE / "annotations/tanvi" / f"{t}.csv", rows)
        print("written to", HERE / "annotations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
