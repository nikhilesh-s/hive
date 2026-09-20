"""Local-runner bridge: hosted HiveBlot asks the RESEARCHER'S machine to run
model jobs, so Claude Code credentials never leave that machine.

    hosted API  --submit-->  job relay  <--poll--  HiveBlot Local Runner
                                                        |
                                                   local `claude -p`

Design rules (see research/LOCAL_RUNNER.md for the threat model):

* A job carries ONLY prompt strings, an optional image data URL, a token
  budget and a job kind from a fixed allowlist. It can never carry a command,
  a path, CLI flags or an executable name — the runner builds those itself.
* The runner is outbound-only: it polls this relay over HTTPS. The laptop
  needs no inbound port and no public address.
* Two secrets, both held by the runner, neither ever sent to a browser: the
  runner token (proves "I am the researcher's runner") and a per-job HMAC
  token issued at claim time (proves "I am the runner that claimed THIS job"),
  so a second runner cannot answer someone else's job.
* Nothing about the researcher's Claude login (cookies, session files, env)
  is ever requested, transmitted or logged. The relay never sees it.

ponytail: the queue is in-process, which fits one hosted instance. Moving it
to a table is a drop-in change (submit/claim/complete are the only writers);
do that when the hosted API runs more than one worker.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..limiter import limiter

logger = logging.getLogger("hive.experimental.runner")

# The only model jobs a hosted HiveBlot may ask a local runner to run.
JOB_KINDS = ("extract_panel", "paper_qa")
JobKind = Literal["extract_panel", "paper_qa"]

CLAIM_TIMEOUT_S = 240.0      # a claimed job whose runner vanished returns to the queue
JOB_TTL_S = 900.0            # finished/abandoned jobs are forgotten after this
ONLINE_WINDOW_S = 75.0       # a runner that polled within this window counts as connected
MAX_PROMPT_CHARS = 200_000
MAX_IMAGE_CHARS = 12_000_000


def _runner_secret() -> str:
    """Shared secret for the runner endpoints (never the internal API key, so a
    leaked runner token cannot read the corpus)."""
    return os.environ.get("HIVEBLOT_RUNNER_TOKEN", "") or getattr(settings, "runner_token", "") or ""


@dataclass
class Job:
    id: str
    kind: str
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    claimed_at: float | None = None
    claim_token: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    # threading, not asyncio: extraction and paper QA call the provider from a
    # worker thread, so the waiter is not always on the event loop.
    done: threading.Event = field(default_factory=threading.Event)

    @property
    def state(self) -> str:
        if self.result is not None or self.error is not None:
            return "done"
        return "claimed" if self.claimed_at is not None else "queued"


JOBS: dict[str, Job] = {}
_LAST_POLL: float = 0.0


def runner_online() -> bool:
    return (time.time() - _LAST_POLL) < ONLINE_WINDOW_S


def runner_configured() -> bool:
    return bool(_runner_secret())


def status() -> dict[str, Any]:
    queued = sum(1 for j in JOBS.values() if j.state == "queued")
    return {"configured": runner_configured(), "online": runner_online(),
            "seconds_since_poll": None if not _LAST_POLL else round(time.time() - _LAST_POLL, 1),
            "queued": queued, "in_flight": sum(1 for j in JOBS.values() if j.state == "claimed")}


def _reap() -> None:
    now = time.time()
    for jid, job in list(JOBS.items()):
        if job.state == "claimed" and job.claimed_at and now - job.claimed_at > CLAIM_TIMEOUT_S:
            # the runner died mid-job: requeue it once, the work is idempotent
            job.claimed_at, job.claim_token = None, None
            logger.warning("model job %s returned to the queue (runner timeout)", jid)
        elif job.state == "done" and now - job.created_at > JOB_TTL_S:
            JOBS.pop(jid, None)


def _claim_token(job_id: str) -> str:
    return hmac.new(_runner_secret().encode(), f"claim:{job_id}".encode(), hashlib.sha256).hexdigest()


def submit(kind: str, payload: dict[str, Any]) -> Job:
    if kind not in JOB_KINDS:
        raise ValueError(f"unknown model job kind: {kind}")
    if len(str(payload.get("system", ""))) + len(str(payload.get("user", ""))) > MAX_PROMPT_CHARS:
        raise ValueError("prompt too large for a model job")
    if len(str(payload.get("image_data_url") or "")) > MAX_IMAGE_CHARS:
        raise ValueError("image too large for a model job")
    _reap()
    job = Job(id=uuid.uuid4().hex, kind=kind, payload={
        # an explicit whitelist: nothing else from the caller reaches the runner
        "system": str(payload.get("system", "")),
        "user": str(payload.get("user", "")),
        "max_tokens": int(payload.get("max_tokens") or 1200),
        "image_data_url": payload.get("image_data_url") or None,
        "json": bool(payload.get("json")),
        "schema": payload.get("schema") or None,
    })
    JOBS[job.id] = job
    return job


def wait_for_result(job: Job, timeout: float) -> dict[str, Any]:
    """Block the calling worker thread until the local runner answers."""
    if not job.done.wait(timeout):
        JOBS.pop(job.id, None)
        raise TimeoutError("the local Claude runner did not answer in time")
    if job.error:
        raise RuntimeError(job.error)
    return job.result or {}


# --- runner-facing endpoints (runner token, NOT the internal API key) --------

router = APIRouter(prefix="/experimental/runner", tags=["experimental-runner"])


class ResultIn(BaseModel):
    job_token: str = Field(max_length=200)
    result: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=2000)


def _auth(authorization: str | None) -> None:
    secret = _runner_secret()
    if not secret:
        raise HTTPException(503, "The local-runner bridge is not configured on this server")
    presented = (authorization or "").removeprefix("Bearer ").strip()
    if not presented or not hmac.compare_digest(presented, secret):
        raise HTTPException(401, "Invalid runner token")


@router.get("/jobs")
@limiter.limit("240/minute")
async def claim_job(request: Request, wait: float = 20.0, authorization: str | None = Header(default=None)):
    """Long-poll for one job. The runner never receives anything but prompts."""
    global _LAST_POLL
    _auth(authorization)
    _LAST_POLL = time.time()
    deadline = time.time() + max(0.0, min(float(wait), 55.0))
    while True:
        _reap()
        for job in sorted((j for j in JOBS.values() if j.state == "queued"), key=lambda j: j.created_at):
            job.claimed_at = time.time()
            job.claim_token = _claim_token(job.id)
            logger.info("model job %s (%s) claimed by the local runner", job.id, job.kind)
            return {"job": {"id": job.id, "kind": job.kind, "job_token": job.claim_token, **job.payload}}
        if time.time() >= deadline:
            return {"job": None}
        await asyncio.sleep(0.25)


@router.post("/jobs/{job_id}/result")
@limiter.limit("240/minute")
async def submit_result(request: Request, job_id: str, body: ResultIn,
                        authorization: str | None = Header(default=None)):
    _auth(authorization)
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job")
    if not job.claim_token or not hmac.compare_digest(body.job_token, job.claim_token):
        raise HTTPException(403, "This job was not claimed with that token")
    if job.state == "done":
        return {"job_id": job_id, "accepted": False, "reason": "already answered"}
    if body.error:
        job.error = body.error[:2000]
    else:
        job.result = body.result or {}
    job.done.set()
    return {"job_id": job_id, "accepted": True}


@router.get("/status")
async def runner_status(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return status()
