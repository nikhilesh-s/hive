"""Model plumbing shared by extraction and paper QA: the claude_cli provider
(argument shape, envelope parsing, error handling, temp-image lifecycle),
backend_status as the single readiness source, ask() routing through the
configured provider, and the OpenAI generator being lazy/optional."""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

import pytest

from app.experimental import ask, ingest  # noqa: F401  (puts the repo root on sys.path)
from western_blot_miner import llm_client

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _envelope(result, **extra):
    env = {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
           "result": result, "modelUsage": {"claude-haiku-4-5-20251001": {}, "claude-sonnet-5": {}}}
    env.update(extra)
    return json.dumps(env)


class Recorder:
    def __init__(self, rc=0, out="", err="", on_call=None):
        self.rc, self.out, self.err, self.on_call = rc, out, err, on_call
        self.calls = []

    def __call__(self, args, cwd):
        self.calls.append((args, cwd))
        if self.on_call:
            self.on_call(args, cwd)
        return self.rc, self.out, self.err


def test_cli_text_request_shape_and_result():
    rec = Recorder(out=_envelope("The answer cites [E1]."))
    c = llm_client.ClaudeCLIClient(model="sonnet", executable="/bin/sh", runner=rec)
    text, model = c.complete_text("SYS", "USER")
    assert text == "The answer cites [E1]." and model == "claude-sonnet-5"
    args, cwd = rec.calls[0]
    assert args[:3] == ["/bin/sh", "-p", "USER"]
    assert args[args.index("--system-prompt") + 1] == "SYS"
    assert args[args.index("--tools") + 1] == ""                      # no tools for text
    assert "--no-session-persistence" in args and "--disable-slash-commands" in args
    # the operator's user plugins / hooks / output styles must not shape answers
    assert args[args.index("--setting-sources") + 1] == "project"
    assert "--bare" not in args and "--dangerously-skip-permissions" not in args
    assert os.path.isdir(cwd) and not os.listdir(cwd)                   # private empty cwd


def test_cli_json_request_parses_result():
    rec = Recorder(out=_envelope('```json\n{"rows": [{"target": "STAT3"}]}\n```'))
    c = llm_client.ClaudeCLIClient(executable="/bin/sh", runner=rec)
    assert c.complete_json("S", "U") == {"rows": [{"target": "STAT3"}]}


def test_cli_image_request_writes_temp_file_allows_only_read_and_cleans_up():
    seen = {}

    def on_call(args, cwd):
        seen["cwd"] = cwd
        seen["files"] = os.listdir(cwd)
        seen["exists"] = Path(cwd, "panel.png").is_file()
        seen["prompt"] = args[2]
    rec = Recorder(out=_envelope('{"lanes": 6}'), on_call=on_call)
    c = llm_client.ClaudeCLIClient(executable="/bin/sh", runner=rec)
    data_url = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()
    assert c.complete_json("S", "Count lanes.", image_data_url=data_url) == {"lanes": 6}
    args, cwd = rec.calls[0]
    assert seen["files"] == ["panel.png"] and seen["exists"]
    assert args[args.index("--tools") + 1] == "Read" and args[args.index("--allowedTools") + 1] == "Read"
    assert args[args.index("--add-dir") + 1] == cwd == seen["cwd"]
    assert "panel.png" in seen["prompt"] and "Read tool" in seen["prompt"]
    assert not Path(cwd).exists()                                        # cleaned up


def test_cli_error_paths():
    c = llm_client.ClaudeCLIClient(executable="/bin/sh", runner=Recorder(rc=1, err="boom"))
    with pytest.raises(RuntimeError, match="exit 1"):
        c.complete_text("S", "U")
    c = llm_client.ClaudeCLIClient(executable="/bin/sh", runner=Recorder(out="not json"))
    with pytest.raises(RuntimeError, match="non-JSON"):
        c.complete_text("S", "U")
    c = llm_client.ClaudeCLIClient(executable="/bin/sh",
                                   runner=Recorder(out=_envelope("Rate limited", is_error=True, subtype="error_during_execution")))
    with pytest.raises(RuntimeError, match="claude CLI error"):
        c.complete_text("S", "U")
    c = llm_client.ClaudeCLIClient(executable="", runner=Recorder())
    c.executable = ""
    with pytest.raises(RuntimeError, match="not found"):
        c.complete_text("S", "U")


def test_backend_status_is_the_single_readiness_source(monkeypatch):
    monkeypatch.setenv("WBM_LLM_BACKEND", "claude_cli")
    monkeypatch.setenv("CLAUDE_CLI", "/definitely/missing/claude")
    ok, why = llm_client.backend_status()
    assert not ok and "claude" in why
    assert ingest.backend_ready() == (ok, why) and ask.llm_ready() is False
    monkeypatch.setenv("CLAUDE_CLI", "/bin/sh")
    assert llm_client.backend_status() == (True, "claude_cli") and ask.llm_ready() is True
    monkeypatch.delenv("WBM_LLM_BACKEND", raising=False)
    assert llm_client.backend_status()[0] is False
    monkeypatch.setenv("WBM_LLM_BACKEND", "mock")
    assert llm_client.get_client().name == "mock"
    monkeypatch.setenv("WBM_LLM_BACKEND", "claude_cli")
    assert isinstance(llm_client.get_client(), llm_client.ClaudeCLIClient)


def test_ask_routes_through_the_configured_provider(monkeypatch):
    async def fake_query(sql):
        return [{"id": 1, "paper_id": "10.1000/x", "doi": "10.1000/x", "target": "STAT3", "stable_row_key": "k:1",
                 "lane_condition": "0 min", "band_state": "present", "needs_review": False, "page": 2}]
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    monkeypatch.setenv("WBM_LLM_BACKEND", "mock")
    monkeypatch.setattr(llm_client, "get_client",
                        lambda backend=None, escalation=False: llm_client.MockLLMClient(lambda s, u: "STAT3 was blotted [E1]."))
    out = asyncio.run(ask.answer("Was STAT3 blotted?", include_live=False))
    assert out["answer"] == "STAT3 was blotted [E1]." and out["cited"] == ["E1"] and out["model"] == "mock"
