"""Valency Bond client (paper discovery) — MCP JSON-RPC over streamable HTTP.

Valency exposes 38 MCP tools (semantic_search_papers, search_by_title,
filter_papers_with_doi, get_citing_papers, ...). We talk to it server-side
only, with the bearer token from VALENCY_API_TOKEN; the browser never sees it.

The exact argument names of each tool are read from `tools/list` at runtime
(the docs list tool names but not schemas), so `search_papers` adapts to
whatever the live schema calls its query / limit fields. A `transport`
callable can be injected for tests.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

import requests

logger = logging.getLogger("hive.valency")

DEFAULT_URL = "https://mcp.valency.io/"
PROTOCOL = "2024-11-05"
SEARCH_TOOLS = ("semantic_search_papers", "search_by_abstract", "search_by_title")
_QUERY_KEYS = ("query", "q", "text", "search", "title", "abstract")
_LIMIT_KEYS = ("limit", "top_k", "max_results", "n", "k", "num_results")


class ValencyError(RuntimeError):
    pass


def _parse_body(text: str, content_type: str) -> dict:
    """Streamable-HTTP servers may answer JSON or an SSE stream; take the last JSON-RPC message."""
    if "text/event-stream" in content_type:
        last = None
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    last = json.loads(line[5:].strip())
                except ValueError:
                    continue
        if last is None:
            raise ValencyError("empty SSE response")
        return last
    return json.loads(text)


class ValencyClient:
    def __init__(self, token: str, url: str = DEFAULT_URL,
                 transport: Callable[[dict], dict] | None = None, timeout: int = 60):
        if not token and transport is None:
            raise ValencyError("VALENCY_API_TOKEN is not configured")
        self.token, self.url, self.timeout = token, url, timeout
        self._transport = transport or self._http
        self._id = 0
        self._tools: list[dict] | None = None

    # --- transport ---------------------------------------------------------
    def _http(self, payload: dict) -> dict:
        resp = requests.post(self.url, json=payload, timeout=self.timeout, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"})
        if resp.status_code >= 400:
            raise ValencyError(f"Valency HTTP {resp.status_code}: {resp.text[:200]}")
        return _parse_body(resp.text, resp.headers.get("content-type", ""))

    def _rpc(self, method: str, params: dict | None = None) -> Any:
        self._id += 1
        msg = self._transport({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        if "error" in msg:
            raise ValencyError(f"{method}: {msg['error']}")
        return msg.get("result")

    # --- MCP ---------------------------------------------------------------
    def initialize(self) -> dict:
        return self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                        "clientInfo": {"name": "hiveblot", "version": "0.1"}}) or {}

    def list_tools(self) -> list[dict]:
        if self._tools is None:
            self._tools = (self._rpc("tools/list") or {}).get("tools", [])
        return self._tools

    def call_tool(self, name: str, arguments: dict) -> Any:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments}) or {}
        if result.get("isError"):
            raise ValencyError(f"{name}: {result.get('content')}")
        # Tool results arrive as content blocks; structured JSON is usually in a text block.
        if "structuredContent" in result:
            return result["structuredContent"]
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except ValueError:
            return joined

    # --- HiveBlot use ------------------------------------------------------
    def _arg_names(self, tool: dict) -> tuple[str, str | None]:
        props = ((tool.get("inputSchema") or {}).get("properties") or {})
        q = next((k for k in _QUERY_KEYS if k in props), None) or (next(iter(props), "query"))
        lim = next((k for k in _LIMIT_KEYS if k in props), None)
        return q, lim

    def search_papers(self, query: str, limit: int = 10) -> list[dict]:
        tools = {t["name"]: t for t in self.list_tools()}
        name = next((n for n in SEARCH_TOOLS if n in tools), None)
        if name is None:
            raise ValencyError("no paper search tool exposed by the server")
        qkey, lkey = self._arg_names(tools[name])
        args = {qkey: query}
        if lkey:
            args[lkey] = limit
        raw = self.call_tool(name, args)
        return [normalize_paper(p, name) for p in _as_list(raw)][:limit]


def _as_list(raw: Any) -> list[dict]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        for key in ("papers", "results", "items", "data"):
            if isinstance(raw.get(key), list):
                return [r for r in raw[key] if isinstance(r, dict)]
    return []


def normalize_paper(p: dict, tool: str) -> dict:
    """Valency result -> the PaperSearchResult shape the frontend renders."""
    authors = p.get("authors") or p.get("author") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]
    doi = (p.get("doi") or "") or ""
    year = p.get("year") or (str(p.get("published") or p.get("date") or "")[:4] or None)
    return {
        "title": p.get("title"), "authors": [str(a) for a in authors][:6],
        "abstract": p.get("abstract") or p.get("summary"),
        "doi": doi.lower() or None, "year": year,
        "venue": p.get("venue") or p.get("journal") or p.get("primary_category") or p.get("category"),
        "arxiv_id": p.get("arxiv_id") or p.get("id"),
        "url": p.get("url") or p.get("pdf_url") or (f"https://doi.org/{doi}" if doi else None),
        "source": f"valency:{tool}",
    }
