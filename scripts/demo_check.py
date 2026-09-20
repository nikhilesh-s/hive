"""Pre-demo check for the local UCSF stack. PASS / WARN / FAIL per item.

    .venv/bin/python scripts/demo_check.py            # assumes API on :8010, web on :3000
    .venv/bin/python scripts/demo_check.py --api http://127.0.0.1:8010 --web http://localhost:3000

Checks: git branch, `claude` executable + one real noninteractive inference,
required env NAMES (values never printed), API health + experimental status,
live-tier prerequisites, Valency or PMC discovery, one known reviewed
evidence retrieval, a paper-QA (retrieval) response, web page health.
Optional pieces (densitometry, Valency) only WARN. Exit 1 on any FAIL.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPECTED_BRANCH = "experimental/ucsf-demo-2026-09-09"
RESULTS: list[tuple[str, str, str]] = []


def rec(level: str, name: str, detail: str = "") -> None:
    RESULTS.append((level, name, detail))
    print(f"[{level:4}] {name}{' — ' + detail if detail else ''}")


def env_file_has(name: str) -> bool:
    if os.environ.get(name):
        return True
    for f in (REPO / "api" / ".env", REPO / "api" / ".env.cloud"):
        if f.exists() and any(l.startswith(f"{name}=") and l.split("=", 1)[1].strip() for l in f.read_text().splitlines()):
            return True
    return False


def env_file_get(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for f in (REPO / "api" / ".env.cloud", REPO / "api" / ".env"):
        if f.exists():
            for l in f.read_text().splitlines():
                if l.startswith(f"{name}=") and l.split("=", 1)[1].strip():
                    return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def http(method: str, url: str, body: dict | None = None, key: str = "", timeout: int = 60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json",
                                 **({"Authorization": f"Bearer {key}"} if key else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8010")
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--skip-claude", action="store_true", help="skip the real CLI inference")
    a = ap.parse_args()

    # 1. branch
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    rec("PASS" if branch == EXPECTED_BRANCH else "WARN", "git branch", f"{branch} (expected {EXPECTED_BRANCH})")

    # 2. claude executable + inference
    exe = os.environ.get("CLAUDE_CLI") or shutil.which("claude")
    if not exe:
        rec("FAIL", "claude executable", "not found on PATH (set CLAUDE_CLI)")
    else:
        rec("PASS", "claude executable", exe)
        if not a.skip_claude:
            t = time.time()
            try:
                p = subprocess.run([exe, "-p", 'Reply with JSON {"ok": true}', "--output-format", "json",
                                    "--system-prompt", "Reply with the requested JSON only.", "--tools", "",
                                    "--no-session-persistence", "--disable-slash-commands",
                                    "--setting-sources", "project", "--model",
                                    os.environ.get("WBM_MODEL", "sonnet")],
                                   capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                   env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"})
                env = json.loads(p.stdout) if p.returncode == 0 else {}
                ok = p.returncode == 0 and not env.get("is_error") and '"ok"' in str(env.get("result", ""))
                rec("PASS" if ok else "FAIL", "claude -p inference", f"{time.time() - t:.1f}s, exit {p.returncode}" + ("" if ok else f", {p.stderr[-160:].strip()}"))
            except Exception as e:
                rec("FAIL", "claude -p inference", str(e)[:160])

    # 3. env names (never values)
    for name, level in (("INTERNAL_API_KEY", "FAIL"), ("DB_READONLY_URL", "FAIL"), ("DB_INGEST_URL", "FAIL"),
                        ("WBM_LLM_BACKEND", "FAIL"), ("VALENCY_API_TOKEN", "WARN")):
        rec("PASS" if env_file_has(name) else level, f"env {name}", "present" if env_file_has(name) else "absent")

    key = env_file_get("INTERNAL_API_KEY")

    # 4. API
    st, _ = http("GET", f"{a.api}/health")
    rec("PASS" if st == 200 else "FAIL", "API /health", f"{a.api} -> {st}")
    if st != 200:
        return finish()
    st, status = http("GET", f"{a.api}/experimental/status", key=key)
    if st != 200:
        rec("FAIL", "experimental status", f"HTTP {st} (internal key mismatch?)")
        return finish()
    rec("PASS" if status.get("model_backend_ready") else "FAIL", "model backend", str(status.get("model_backend")))
    rec("PASS" if status.get("ingest_db_configured") else "FAIL", "live tier configured", f"live rows: {status.get('live_rows')}")
    rec("PASS" if status.get("valency_configured") else "WARN", "Valency configured", "yes" if status.get("valency_configured") else "no (PMC fallback)")

    # 5. discovery
    st, disc = http("POST", f"{a.api}/experimental/papers/search", {"query": "STAT3 phosphorylation hepatocellular carcinoma western blot", "limit": 5}, key)
    n = len(disc.get("results", [])) if st == 200 else 0
    rec("PASS" if n else "FAIL", "paper discovery", f"{n} results via {disc.get('sources_used')} {disc.get('errors') or ''}")

    # 6. known reviewed evidence
    st, s = http("POST", f"{a.api}/search", {"query": "phospho STAT3 Tyr705"}, key)
    rec("PASS" if st == 200 and s.get("count") == 18 else "FAIL", "reviewed evidence retrieval", f"phospho STAT3 Tyr705 -> {s.get('count')} rows (expect 18)")

    # 7. live tier papers (pre-warmed)
    st, lp = http("GET", f"{a.api}/experimental/live/papers", key=key)
    papers = lp.get("papers", []) if st == 200 else []
    rec("PASS" if papers else "WARN", "pre-warmed live papers", f"{len(papers)}: " + ", ".join(p["doi"] for p in papers[:4]))

    # 8. paper QA (retrieval; model optional)
    st, q = http("POST", f"{a.api}/experimental/ask", {"question": "Is STAT3 phosphorylated at Tyr705 after IL-6 in Hep3B?", "include_live": False}, key, timeout=180)
    ev = len(q.get("evidence", [])) if st == 200 else 0
    rec("PASS" if ev else "FAIL", "paper QA retrieval", f"{ev} evidence blocks; answer={'yes' if q.get('answer') else 'none'}; cited={q.get('cited')}; {q.get('note') or ''}")

    # 9. optional densitometry: diagnostic call on the first search hit, then the
    #    product path (region + researcher lanes) on the STAT3 panel of record 4455
    #    if that record exists locally (P-STAT3 (Ser727) strip, panel C)
    st, d = http("POST", f"{a.api}/experimental-densitometry", {"record_id": (s.get("results") or [{}])[0].get("id")}, key)
    rec("PASS" if st == 200 else "WARN", "densitometry (optional, diagnostic lanes)", f"HTTP {st} · {d.get('quality', {}).get('state', '?') if st == 200 else ''}")
    edges = [793, 894, 996, 1098, 1199, 1301, 1402]
    st, d = http("POST", f"{a.api}/experimental-densitometry",
                 {"record_id": 4455, "region": [793, 120, 1402, 185],
                  "lane_bounds": [[edges[i], edges[i + 1]] for i in range(6)]}, key)
    if st == 200:
        q = d.get("quality", {}).get("state")
        rec("PASS" if q == "ok" and d.get("lane_mode") == "explicit" else "WARN", "densitometry (region + lanes, record 4455)",
            f"state={q} · lanes={d.get('lane_mode')} · ranking_stable={(d.get('stability') or {}).get('ranking_stable')}")
    else:
        rec("WARN", "densitometry (region + lanes, record 4455)", f"HTTP {st} (record 4455 not in this DB?)")

    # 10. web
    for path in ("/", "/experimental/research", "/api/experimental/status"):
        try:
            with urllib.request.urlopen(f"{a.web}{path}", timeout=60) as r:
                rec("PASS" if r.status == 200 else "FAIL", f"web {path}", str(r.status))
        except Exception as e:
            rec("FAIL", f"web {path}", str(e)[:120])
    return finish()


def finish() -> int:
    fails = [r for r in RESULTS if r[0] == "FAIL"]
    warns = [r for r in RESULTS if r[0] == "WARN"]
    print(f"\n{len(RESULTS) - len(fails) - len(warns)} PASS · {len(warns)} WARN · {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
