"""Provider-agnostic LLM client for semantic extraction.

Bedrock-first (correction 6): the default backend is Amazon Bedrock via the
``converse`` API, so the hackathon runs on Bedrock with no RunPod dependency.
The same interface also targets Anthropic-direct, OpenAI, any
OpenAI-compatible server (vLLM/local), and an already-authenticated local
Claude Code install (``claude_cli``), selected by ``WBM_LLM_BACKEND``.

A ``MockLLMClient`` returns canned structured output so the extraction and
reconciliation logic is fully testable offline (no cloud, no keys).
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional


# Cheap "normal extraction" default and the escalation model, both on Bedrock.
DEFAULT_BEDROCK_MODEL = os.environ.get("WBM_BEDROCK_MODEL", "anthropic.claude-3-5-haiku-20241022-v1:0")
DEFAULT_BEDROCK_ESCALATION_MODEL = os.environ.get(
    "WBM_BEDROCK_ESCALATION_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)


def _extract_json(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                pass
    return {"error": "bad_json", "raw": raw[:1200]}


class LLMClient:
    """Interface: return parsed JSON for a (system, user, optional image) prompt."""

    name = "base"
    model = "unknown"

    def complete_json(
        self,
        system: str,
        user: str,
        image_data_url: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def complete_text(self, system: str, user: str, max_tokens: int = 1200) -> tuple[str, str]:
        """Plain-prose completion (paper QA). Returns (text, model name)."""
        raise NotImplementedError


class BedrockClient(LLMClient):
    """Amazon Bedrock via the Converse API (boto3). Default backend."""

    name = "bedrock"

    def __init__(self, model: Optional[str] = None, region: Optional[str] = None):
        self.model = model or DEFAULT_BEDROCK_MODEL
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        import boto3  # lazy: only needed for a live Bedrock call

        client = boto3.client("bedrock-runtime", region_name=self.region)
        content: list[dict] = []
        if image_data_url:
            fmt, data_b64 = _split_data_url(image_data_url)
            import base64
            content.append({"image": {"format": fmt, "source": {"bytes": base64.b64decode(data_b64)}}})
        content.append({"text": user})
        resp = client.converse(
            modelId=self.model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": content}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        parts = resp["output"]["message"]["content"]
        text = "".join(p.get("text", "") for p in parts)
        return _extract_json(text)


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, model: Optional[str] = None):
        # Current-generation default; override with WBM_MODEL. Sampling
        # parameters are not sent: Claude 4.6+ models reject `temperature`
        # and run adaptive thinking by default.
        self.model = model or os.environ.get("WBM_MODEL", "claude-opus-5")

    def complete_json(self, system, user, image_data_url=None, max_tokens=8192, temperature=None):
        import anthropic  # lazy

        client = anthropic.Anthropic()
        content: list[dict] = []
        if image_data_url:
            media_type, data_b64 = _split_media_url(image_data_url)
            content.append({"type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": data_b64}})
        content.append({"type": "text", "text": user})
        resp = client.messages.create(
            model=self.model, max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": content}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            raise RuntimeError("model declined this panel (stop_reason=refusal)")
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        return _extract_json(text)

    def complete_text(self, system, user, max_tokens=1200):
        import anthropic  # lazy

        client = anthropic.Anthropic()
        resp = client.messages.create(model=self.model, max_tokens=max_tokens, system=system,
                                      messages=[{"role": "user", "content": user}])
        if getattr(resp, "stop_reason", None) == "refusal":
            raise RuntimeError("model declined to answer (stop_reason=refusal)")
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        return text.strip(), getattr(resp, "model", self.model)


class OpenAICompatibleClient(LLMClient):
    """OpenAI or any OpenAI-compatible server (vLLM / local). Not RunPod-pinned."""

    name = "openai_compatible"

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("WBM_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("WBM_LLM_API_KEY", "") or os.environ.get("OPENAI_KEY", "")
        self.model = model or os.environ.get("WBM_LLM_MODEL", "gpt-4.1-mini")

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        import requests  # lazy

        user_content: list[dict] = []
        if image_data_url:
            user_content.append({"type": "image_url", "image_url": {"url": image_data_url}})
        user_content.append({"type": "text", "text": user})
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user_content}]},
            timeout=int(os.environ.get("WBM_LLM_TIMEOUT", "120")),
        )
        resp.raise_for_status()
        return _extract_json(resp.json()["choices"][0]["message"]["content"])

    def complete_text(self, system, user, max_tokens=1200):
        import requests  # lazy

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=int(os.environ.get("WBM_LLM_TIMEOUT", "120")),
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip(), self.model


class ClaudeCLIClient(LLMClient):
    """Claude through an already-authenticated Claude Code install (`claude -p`).

    For LOCAL development and demos with no ANTHROPIC_API_KEY: the CLI uses
    the user's interactive Claude Code login. Print mode, JSON envelope, a
    custom system prompt (keeps the context small), no session persistence,
    no slash commands, and NO tools for text/JSON requests. Image requests
    write the panel to a private temp directory, make that directory the
    working directory, and allow exactly the Read tool so Claude can view
    the file; the directory is deleted afterwards. Never `--bare` (that
    would drop the login), never permission-skipping flags.
    """

    name = "claude_cli"
    DEFAULT_MODEL = "sonnet"

    def __init__(self, model: Optional[str] = None, executable: Optional[str] = None,
                 timeout: Optional[int] = None, runner: Optional[Callable[..., tuple[int, str, str]]] = None):
        import shutil

        self.model = model or os.environ.get("WBM_MODEL") or self.DEFAULT_MODEL
        self.executable = self.available(executable)
        self.timeout = int(timeout or os.environ.get("WBM_LLM_TIMEOUT", "300"))
        self._run = runner or self._subprocess

    @staticmethod
    def available(executable: Optional[str] = None) -> str:
        """Path of a runnable `claude` (CLAUDE_CLI override, else PATH) or ''."""
        import shutil

        exe = executable or os.environ.get("CLAUDE_CLI") or "claude"
        return shutil.which(exe) or ""

    def _subprocess(self, args: list[str], cwd: str) -> tuple[int, str, str]:
        import subprocess

        env = dict(os.environ)
        env.pop("CLAUDECODE", None)  # allow a nested launch from inside a Claude session
        try:
            proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                  timeout=self.timeout, stdin=subprocess.DEVNULL, env=env)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timed out after {self.timeout}s") from e
        return proc.returncode, proc.stdout, proc.stderr

    def _invoke(self, system: str, user: str, *, schema: Optional[dict] = None,
                image_dir: Optional[str] = None) -> dict:
        import tempfile

        if not self.executable:
            raise RuntimeError("claude CLI not found (set CLAUDE_CLI or install Claude Code)")
        # --setting-sources project: the operator's USER settings (plugins, hooks,
        # output styles) must not shape extraction or answers. On the demo laptop
        # a user style hook turned paper-QA answers into clipped non-grammatical
        # prose; the login is unaffected (unlike --bare).
        args = [self.executable, "-p", user, "--output-format", "json",
                "--system-prompt", system, "--model", self.model,
                "--no-session-persistence", "--disable-slash-commands",
                "--setting-sources", "project"]
        if image_dir:
            args += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", image_dir]
            cwd = image_dir
        else:
            args += ["--tools", ""]
            cwd = tempfile.mkdtemp(prefix="hiveblot-cli-")
        if schema:
            args += ["--json-schema", json.dumps(schema)]
        rc, out, err = self._run(args, cwd)
        if rc != 0:
            raise RuntimeError(f"claude CLI exit {rc}: {(err or out)[-400:].strip()}")
        try:
            env = json.loads(out)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"claude CLI returned non-JSON output: {out[:200]!r}") from e
        if isinstance(env, list):  # stream-style array: last message is the result
            env = env[-1] if env else {}
        if env.get("is_error") or env.get("subtype") not in (None, "success"):
            raise RuntimeError(f"claude CLI error: {env.get('subtype')}: {str(env.get('result'))[:300]}")
        return env

    def _model_used(self, env: dict) -> str:
        used = [m for m in (env.get("modelUsage") or {}) if "haiku" not in m] or list(env.get("modelUsage") or {})
        return used[0] if used else self.model

    def complete_json(self, system, user, image_data_url=None, max_tokens=8192, temperature=None):
        import base64
        import shutil
        import tempfile

        if not image_data_url:
            env = self._invoke(system, user)
            return _extract_json(str(env.get("result", "")))
        media_type, data_b64 = _split_media_url(image_data_url)
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}.get(media_type, "png")
        tmpdir = tempfile.mkdtemp(prefix="hiveblot-panel-")
        try:
            path = os.path.join(tmpdir, f"panel.{ext}")
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(data_b64))
            prompt = (f"{user}\n\nThe Western blot panel image for this request is the file `{path}` "
                      f"(the only file in your working directory). Use the Read tool to view it, "
                      f"then answer with the JSON described above and nothing else.")
            env = self._invoke(system, prompt, image_dir=tmpdir)
            return _extract_json(str(env.get("result", "")))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def complete_text(self, system, user, max_tokens=1200):
        env = self._invoke(system, user)
        return str(env.get("result", "")).strip(), self._model_used(env)


class MockLLMClient(LLMClient):
    """Returns canned structured output. For offline tests / the benchmark."""

    name = "mock"
    model = "mock"

    def __init__(self, responder: Callable[[str, str], dict] | dict):
        self._responder = responder

    def complete_json(self, system, user, image_data_url=None, max_tokens=4096, temperature=0.0):
        if callable(self._responder):
            return self._responder(system, user)
        return dict(self._responder)

    def complete_text(self, system, user, max_tokens=1200):
        out = self._responder(system, user) if callable(self._responder) else self._responder
        return (out if isinstance(out, str) else json.dumps(out)), "mock"


def backend_status(backend: Optional[str] = None) -> tuple[bool, str]:
    """Is the configured backend usable right now? (ok, backend name | reason)."""
    backend = (backend or os.environ.get("WBM_LLM_BACKEND", "")).lower()
    env = os.environ
    if backend == "claude_cli":
        exe = ClaudeCLIClient.available()
        return (True, "claude_cli") if exe else (False, "WBM_LLM_BACKEND=claude_cli but no `claude` executable found")
    if backend == "anthropic":
        ok = bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))
        return ok, "anthropic" if ok else "WBM_LLM_BACKEND=anthropic but no ANTHROPIC_API_KEY"
    if backend == "bedrock":
        ok = bool(env.get("AWS_ACCESS_KEY_ID") or env.get("AWS_PROFILE"))
        return ok, "bedrock" if ok else "WBM_LLM_BACKEND=bedrock but no AWS credentials"
    if backend in ("openai", "openai_compatible"):
        ok = bool(env.get("WBM_LLM_API_KEY") or env.get("OPENAI_API_KEY") or env.get("OPENAI_KEY"))
        return ok, backend if ok else "WBM_LLM_BACKEND=openai but no WBM_LLM_API_KEY"
    if backend == "mock":
        return True, "mock"
    return False, "No extraction model configured (set WBM_LLM_BACKEND=claude_cli|anthropic|bedrock|openai + credentials)"


def get_client(backend: Optional[str] = None, escalation: bool = False) -> LLMClient:
    backend = (backend or os.environ.get("WBM_LLM_BACKEND", "bedrock")).lower()
    if backend == "bedrock":
        return BedrockClient(model=DEFAULT_BEDROCK_ESCALATION_MODEL if escalation else None)
    if backend == "anthropic":
        return AnthropicClient()
    if backend == "claude_cli":
        return ClaudeCLIClient()
    if backend in ("openai", "openai_compatible"):
        return OpenAICompatibleClient()
    if backend == "mock":
        return MockLLMClient({"error": "mock not configured"})
    raise ValueError(f"unknown WBM_LLM_BACKEND: {backend}")


def _split_data_url(data_url: str) -> tuple[str, str]:
    # data:image/png;base64,XXXX -> ("png", "XXXX")
    header, b64 = data_url.split(",", 1)
    media = header.split(";")[0].replace("data:image/", "")
    return media, b64


def _split_media_url(data_url: str) -> tuple[str, str]:
    header, b64 = data_url.split(",", 1)
    media_type = header.replace("data:", "").split(";")[0]
    return media_type, b64
