#!/usr/bin/env python3
"""Deterministic paper draw and per-paper panel sampling sequences (PREREGISTRATION.md §4, §6).

    .venv/bin/python eval/blind_2026_10/draw.py
"""
import hashlib
import random

SEED = 20261018
ELIGIBLE = [
    "PMC5328321", "PMC5225179", "PMC8332585", "PMC4393234", "PMC12022650",
    "PMC8632698", "PMC6406374", "PMC7333534", "PMC7948984", "PMC6794468",
    "PMC9283986", "PMC3941594", "PMC7757890", "PMC6242874", "PMC6360618",
]


def draw_order() -> list[str]:
    order = sorted(ELIGIBLE)
    random.Random(SEED).shuffle(order)
    return order


def panel_sequence(pmcid: str, length: int = 80) -> list[int]:
    """Random order of inventory panel numbers 1..length, fixed per paper."""
    sub = int(hashlib.sha256(f"{SEED}:{pmcid}".encode()).hexdigest()[:12], 16)
    seq = list(range(1, length + 1))
    random.Random(sub).shuffle(seq)
    return seq


if __name__ == "__main__":
    for rank, pmcid in enumerate(draw_order(), 1):
        print(rank, pmcid, panel_sequence(pmcid)[:20])
