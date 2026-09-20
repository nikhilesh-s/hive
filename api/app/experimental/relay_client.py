"""`WBM_LLM_BACKEND=relay`: an LLMClient that runs nothing itself and hands the
prompt to the researcher's Local Runner through the job relay.

This keeps the provider abstraction intact — extraction and paper QA call
`complete_json` / `complete_text` exactly as they do for claude_cli, anthropic
or bedrock — while the model call happens on the machine that owns the Claude
login. Switching the hosted service to Bedrock or the Anthropic API later is
still a one-line backend change.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path as _Path
from typing import Any, Optional

_REPO = _Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:  # western_blot_miner (provider plumbing) lives at the repo root
    sys.path.insert(0, str(_REPO))

from western_blot_miner import llm_client  # noqa: E402

from . import runner  # noqa: E402

# A model job waits this long for the researcher's laptop to answer. Extraction
# panels are slower than paper QA, so each call passes its own budget.
DEFAULT_TIMEOUT_S = float(os.environ.get("HIVEBLOT_RELAY_TIMEOUT", "300"))


class RelayLLMClient(llm_client.LLMClient):
    name = "relay"

    def __init__(self, timeout: Optional[float] = None):
        self.timeout = float(timeout or DEFAULT_TIMEOUT_S)
        self.model = "local-runner"

    def _run(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not runner.runner_configured():
            raise RuntimeError("The local-runner bridge is not configured on this server")
        if not runner.runner_online():
            raise RuntimeError("No HiveBlot Local Runner is connected: start it on your machine to run "
                               "model steps (see research/LOCAL_RUNNER.md). Reviewed search, the live "
                               "tier and densitometry do not need it.")
        job = runner.submit(kind, payload)
        return runner.wait_for_result(job, self.timeout)

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        out = self._run("extract_panel", {"system": system, "user": user, "image_data_url": image_data_url,
                                          "max_tokens": max_tokens, "json": True})
        return out.get("json") if isinstance(out.get("json"), dict) else out

    def complete_text(self, system, user, max_tokens=1200):
        out = self._run("paper_qa", {"system": system, "user": user, "max_tokens": max_tokens})
        return str(out.get("text", "")), str(out.get("model") or "local-runner")


def _status(_backend: str) -> tuple[bool, str]:
    if not runner.runner_configured():
        return False, "WBM_LLM_BACKEND=relay but HIVEBLOT_RUNNER_TOKEN is not set on the server"
    if not runner.runner_online():
        return False, "no HiveBlot Local Runner connected (start it on the researcher's machine)"
    return True, "relay (local runner)"


def install() -> None:
    """Make `relay` a first-class backend of the shared provider abstraction."""
    llm_client.register_backend("relay", lambda escalation=False: RelayLLMClient(), _status)
