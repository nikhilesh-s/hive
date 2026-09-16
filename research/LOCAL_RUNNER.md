# HiveBlot Local Runner — hybrid model execution

**Status:** built and tested locally 2026-09-15; **not deployed**. Nothing in
this document changes the laptop demo, which keeps running `claude_cli`
directly.

Hosted HiveBlot holds **no model credential**. Deterministic work (search,
evidence, densitometry, the live tier, feedback) runs in the cloud. The two
steps that need a model — extracting a paper's blots and answering a question
about a paper — are executed on the researcher's own machine by a small runner
that uses their existing Claude Code login.

```
browser ─▶ Vercel ─▶ hosted FastAPI ─▶ Supabase / storage      (deterministic)
                           │
                           ├─ model job needed
                           ▼
                     job relay  ◀── outbound poll ── HiveBlot Local Runner
                           ▲                               │
                           └──── structured result ────────┤
                                                           ▼
                                                    local `claude -p`
                                                  (researcher's login)
```

## Why it is shaped this way

A hosted service that could run `claude` as the user would need that user's
credentials, which is exactly what we refuse to have. Instead the hosted side
can only *ask*, and the laptop decides what it is willing to run.

## The security contract

Enforced in `api/app/experimental/runner.py` and covered by
`api/tests/test_runner_bridge.py` (8 tests):

| Property | How |
|---|---|
| A job is prompts, nothing else | `submit()` rebuilds the payload from a fixed whitelist: `system`, `user`, `max_tokens`, `image_data_url`, `json`, `schema`. Smuggled `executable`, `args`, `cwd`, `env`, `command`, `allowedTools` keys are dropped before the job exists |
| No arbitrary execution | The runner picks the executable and every CLI flag itself; the job kind must be in its own `HANDLERS` allowlist (`extract_panel`, `paper_qa`) or it raises before any provider call |
| No inbound port | The runner polls outbound over HTTPS; the laptop needs no public address and no firewall change |
| Runner authentication | `HIVEBLOT_RUNNER_TOKEN`, compared in constant time, separate from the internal API key — a leaked runner token cannot read the corpus, and the internal key cannot claim jobs |
| Per-job authorisation | Claiming returns an HMAC job token; only that token can post that job's result, and only once (a replay is rejected, not applied) |
| No credential exfiltration | The relay never asks for and never stores Claude session material; the runner sends only the answer. The token never appears in the runner's output |
| Failure is legible | With no runner connected, model actions return "no HiveBlot Local Runner connected", never a hang or a request for an API key |
| Crash recovery | A claimed job whose runner dies returns to the queue after `CLAIM_TIMEOUT_S` and is re-claimable; jobs expire after `JOB_TTL_S` |

Residual risks, stated plainly:

* The relay queue is in-process, so it fits **one** hosted instance. Running
  more than one worker needs the queue moved to a table — `submit` / `claim` /
  `complete` are the only writers.
* Anyone holding the runner token can claim jobs and return fabricated
  answers. The token is per researcher and revocable by rotating the server
  env var; treat it like a password.
* The hosted service sees the prompts it sent and the answers returned, which
  include paper text it already holds. It never sees the local filesystem.
* The runner will run any prompt the hosted service sends within an allowlisted
  job kind. It is not a sandbox for the *content* of prompts, only for their
  *effects* — no shell, no file access, no flags from the network.

## Verified behaviour (2026-09-15, local)

A second API instance started with `WBM_LLM_BACKEND=relay`, no
`ANTHROPIC_API_KEY`, and no `claude_cli` backend:

* **Runner down:** paper QA returned its 3 evidence blocks, `answer: null`, and
  the note `Retrieval only: no HiveBlot Local Runner connected (start it on the
  researcher's machine).`
* **Runner up:** the same question returned a real cited answer
  (`model: claude-sonnet-5`, cites `E1 E2 E3`), produced by `claude -p` on this
  laptop. Job round trip: 6 s.
* The runner's output contained no token, credential or session string.

## Setup for a UCSF tester

1. Install Claude Code and sign in (`claude` must run and answer).
2. Get a runner token from whoever operates the HiveBlot deployment.
3. Run, and leave it running while you use HiveBlot:

```bash
HIVEBLOT_RUNNER_TOKEN=<your token> \
  python3 scripts/hiveblot_runner.py --server https://<hosted-hiveblot-api>
```

It prints one line per job. Stop it with Ctrl-C; the hosted UI then says a
runner is required for model steps, and everything else keeps working.

## Server side

| Setting | Meaning |
|---|---|
| `HIVEBLOT_RUNNER_TOKEN` | Enables the bridge. Unset = the runner routes answer 503 and nothing changes |
| `WBM_LLM_BACKEND=relay` | Send model work to the runner instead of a cloud provider |
| `HIVEBLOT_RELAY_TIMEOUT` | Seconds a hosted request waits for the laptop (default 300) |

`relay` is a normal backend of the existing `LLMClient` abstraction, registered
at startup. Switching the hosted service to Bedrock or the Anthropic API later
remains a one-line backend change; extraction and paper QA do not know the
difference.

## Still required before a hosted experimental deployment

Not done, and each is a deliberate decision rather than a task:

1. Supabase: apply `005_experimental_live_tables` and load the live tier
   (a production schema change plus a data load).
2. API image: add OpenCV and NumPy for densitometry; the current
   `api/requirements.txt` has neither, so hosted measurement would fail at
   import.
3. Panel crops for the record-id path must be served from the API host or
   object storage.
4. Render free tier: ~21 s cold start and a 512 MB instance; 40-megapixel
   measurement needs headroom.
5. The relay queue must move to a table if the API runs more than one worker.
