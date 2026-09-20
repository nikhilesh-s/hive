#!/usr/bin/env python3
"""HiveBlot Local Runner — runs HiveBlot's model steps on YOUR machine.

Hosted HiveBlot never holds a Claude credential. When a hosted action needs a
model (extracting a paper's blots, answering a question about a paper), it
queues a job; this runner picks the job up over an OUTBOUND connection, runs it
through your already-authenticated `claude` install, and posts the answer back.

    hosted HiveBlot  ──queue──▶  job relay  ◀──poll──  this runner ──▶ claude -p

What leaves your machine: the model's answer text (and, for extraction, the
structured JSON it produced).
What never leaves your machine: your Claude login, session files, cookies,
environment, file paths, or anything else on disk. The runner sends no
credentials to HiveBlot and accepts no commands from it — a job is only a
prompt plus an optional image, and the job kind must be one this file knows.

Setup (one line, then leave it running):

    HIVEBLOT_RUNNER_TOKEN=<token from your HiveBlot settings> \\
      python3 scripts/hiveblot_runner.py --server https://<hosted-hiveblot-api>

Requires: a working `claude` CLI (Claude Code), signed in as you.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Jobs this runner is willing to run. A job kind the hosted service invents
# later does nothing here until this list is updated deliberately.
HANDLERS = ("extract_panel", "paper_qa")


def _post(url: str, token: str, body: dict, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _get(url: str, token: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def run_job(job: dict, model: str | None) -> dict:
    """Run ONE allowlisted job through the shared provider abstraction.

    The job supplies prompts only. The executable, its flags and the working
    directory are chosen here, by this file — never by the hosted service.
    """
    from western_blot_miner import llm_client

    kind = job.get("kind")
    if kind not in HANDLERS:
        raise ValueError(f"refusing unknown job kind: {kind!r}")
    client = llm_client.ClaudeCLIClient(model=model)
    system, user = str(job.get("system", "")), str(job.get("user", ""))
    max_tokens = int(job.get("max_tokens") or 1200)
    if kind == "paper_qa":
        text, used = client.complete_text(system, user, max_tokens=max_tokens)
        return {"text": text, "model": used}
    out = client.complete_json(system, user, image_data_url=job.get("image_data_url"), max_tokens=max_tokens)
    return {"json": out, "model": client.model}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run HiveBlot model jobs locally with your own Claude login.")
    ap.add_argument("--server", default=os.environ.get("HIVEBLOT_SERVER", "http://localhost:8010"),
                    help="hosted HiveBlot API base URL")
    ap.add_argument("--token", default=os.environ.get("HIVEBLOT_RUNNER_TOKEN", ""),
                    help="runner token (or HIVEBLOT_RUNNER_TOKEN)")
    ap.add_argument("--model", default=os.environ.get("WBM_MODEL", "sonnet"))
    ap.add_argument("--wait", type=float, default=20.0, help="long-poll seconds per request")
    ap.add_argument("--once", action="store_true", help="handle at most one job, then exit (testing)")
    a = ap.parse_args()
    if not a.token:
        print("error: set HIVEBLOT_RUNNER_TOKEN (get it from your HiveBlot settings)", file=sys.stderr)
        return 2

    from western_blot_miner import llm_client
    if not llm_client.ClaudeCLIClient.available():
        print("error: no `claude` executable found. Install Claude Code and sign in first.", file=sys.stderr)
        return 2

    base = a.server.rstrip("/")
    print(f"HiveBlot Local Runner → {base}\n"
          f"  model: {a.model} · jobs: {', '.join(HANDLERS)}\n"
          f"  your Claude login stays on this machine; only answers are sent back.\n"
          f"  Ctrl-C to stop.", flush=True)
    idle_since = time.time()
    while True:
        try:
            got = _get(f"{base}/experimental/runner/jobs?wait={a.wait}", a.token, timeout=a.wait + 20)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                print("error: the server rejected this runner token", file=sys.stderr)
                return 2
            if e.code == 503:
                print("error: the server has no local-runner bridge configured", file=sys.stderr)
                return 2
            print(f"warn: poll failed ({e.code}); retrying", file=sys.stderr)
            time.sleep(3)
            continue
        except Exception as e:  # network blip: keep trying, the queue is server-side
            print(f"warn: {type(e).__name__} while polling; retrying", file=sys.stderr)
            time.sleep(3)
            continue

        job = got.get("job")
        if not job:
            if time.time() - idle_since > 300:
                print("· waiting for work", flush=True)
                idle_since = time.time()
            continue
        idle_since = time.time()
        jid, token = job.get("id"), job.get("job_token")
        print(f"· job {jid} ({job.get('kind')}) running locally…", flush=True)
        t0 = time.time()
        try:
            result = run_job(job, a.model)
            payload = {"job_token": token, "result": result}
            print(f"· job {jid} done in {time.time() - t0:.0f}s", flush=True)
        except Exception as e:
            payload = {"job_token": token, "error": f"{type(e).__name__}: {e}"[:2000]}
            print(f"· job {jid} failed: {type(e).__name__}", file=sys.stderr, flush=True)
        try:
            _post(f"{base}/experimental/runner/jobs/{jid}/result", a.token, payload)
        except Exception as e:
            print(f"warn: could not deliver the result ({type(e).__name__}); the server will requeue it",
                  file=sys.stderr)
        if a.once:
            return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nHiveBlot Local Runner stopped. Hosted model steps will say a runner is required.")
        raise SystemExit(0)
