"""LLM gateway: one OpenAI-compatible entry point for every model call.

Responsibilities
- Disk cache keyed by sha256(model, messages, decoding params). Reruns are free
  and bit-for-bit reproducible, and the cache itself can be released.
- Structured output: ``json_mode`` (json_object) or ``json_schema`` (strict
  schema; supported by OpenAI and by vLLM's OpenAI server). Parse failures are
  recorded, never silently swallowed, because they are a finding for small models.
- Usage accounting: every call (cached or not) is appended to a JSONL log with a
  caller ``tag`` such as ``cupmem.extract``, which feeds the cost analysis (E4).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

CACHE_VERSION = 1


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Usage
    latency_s: float
    cached: bool = False
    parsed: Any = None
    parse_error: str | None = None

    @property
    def ok_json(self) -> bool:
        return self.parse_error is None and self.parsed is not None


class Backend(Protocol):
    def complete(self, model: str, messages: list[dict], params: dict) -> tuple[str, Usage]: ...


_RETRY_IN = re.compile(r"try again in ([\d.]+)\s*(ms|s)", re.I)


class TPMLimiter:
    """Client-side tokens-per-minute limiter (sliding 60 s window).

    Estimates a request the way OpenAI's limiter does (chars/4 + max output
    tokens), so we wait *before* sending instead of collecting 429s."""

    def __init__(self, tpm: int, window_s: float = 60.0):
        self.tpm, self.window = tpm, window_s
        self._events: list[tuple[float, int]] = []
        self._lock = threading.Lock()

    def acquire(self, n: int) -> None:
        n = min(n, self.tpm)
        while True:
            with self._lock:
                now = time.monotonic()
                self._events = [(t, k) for t, k in self._events if now - t < self.window]
                used = sum(k for _, k in self._events)
                if used + n <= self.tpm:
                    self._events.append((now, n))
                    return
                wait = self.window - (now - self._events[0][0]) + 0.05
            time.sleep(max(wait, 0.05))


def estimate_request_tokens(messages: list[dict], params: dict, default_max_output: int = 16384) -> int:
    chars = sum(len(m.get("content") or "") for m in messages)
    return chars // 4 + int(params.get("max_tokens") or default_max_output)


class OpenAICompatBackend:
    """Works with api.openai.com, vLLM, and any OpenAI-compatible host."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout: float = 600.0, max_retries: int = 2, tpm: int | None = None,
                 rate_limit_retries: int = 12):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key or "EMPTY",
                             timeout=timeout, max_retries=max_retries)
        self.limiter = TPMLimiter(tpm) if tpm else None
        self.rate_limit_retries = rate_limit_retries

    def complete(self, model: str, messages: list[dict], params: dict) -> tuple[str, Usage]:
        from openai import RateLimitError

        if self.limiter:
            self.limiter.acquire(estimate_request_tokens(messages, params))
        for attempt in range(self.rate_limit_retries + 1):
            try:
                resp = self.client.chat.completions.create(model=model, messages=messages, **params)
                break
            except RateLimitError as e:
                if attempt == self.rate_limit_retries or "insufficient_quota" in str(e):
                    raise
                m = _RETRY_IN.search(str(e))
                wait = (float(m.group(1)) / (1000 if m.group(2).lower() == "ms" else 1)) if m else 2 ** attempt
                time.sleep(min(wait + 1.0, 120.0))
        text = resp.choices[0].message.content or ""
        u = resp.usage
        usage = Usage(u.prompt_tokens, u.completion_tokens) if u else Usage()
        return text, usage


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def parse_json_loose(text: str) -> Any:
    """Parse JSON, tolerating code fences and leading/trailing prose."""
    s = text.strip()
    m = _FENCE.search(s)
    if m:
        s = m.group(1)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # fall back to the outermost {...} or [...] span
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = s.find(open_c), s.rfind(close_c)
        if 0 <= i < j:
            try:
                return json.loads(s[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no parseable JSON found")


class _Cache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
        self._conn.commit()
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, json.dumps(value)))
            self._conn.commit()


@dataclass
class UsageTotals:
    calls: int = 0
    cached_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    json_failures: int = 0


class Gateway:
    def __init__(self, backend: Backend, model: str, cache_path: str | Path | None = None,
                 log_path: str | Path | None = None, default_params: dict | None = None,
                 json_repair_retries: int = 1):
        self.backend = backend
        self.model = model
        self.cache = _Cache(Path(cache_path)) if cache_path else None
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_params = {"temperature": 0.0, **(default_params or {})}
        self.json_repair_retries = json_repair_retries
        self.totals: dict[str, UsageTotals] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public
    def chat(self, messages: list[dict] | str, *, tag: str = "untagged", system: str | None = None,
             json_mode: bool = False, json_schema: dict | None = None,
             model: str | None = None, **params: Any) -> LLMResponse:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        model = model or self.model
        call_params = {**self.default_params, **params}
        if json_schema is not None:
            call_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": json_schema.get("title", "output"), "schema": json_schema, "strict": True},
            }
        elif json_mode:
            call_params["response_format"] = {"type": "json_object"}

        resp = self._call(model, messages, call_params, tag)
        if json_mode or json_schema is not None:
            self._attach_json(resp)
            retries = self.json_repair_retries
            while not resp.ok_json and retries > 0:
                retries -= 1
                repair = [*messages, {"role": "assistant", "content": resp.text},
                          {"role": "user", "content": "Your previous reply was not valid JSON. "
                                                      "Reply again with only the JSON object."}]
                resp = self._call(model, repair, call_params, tag + ".repair")
                self._attach_json(resp)
            if not resp.ok_json:
                self._bump(tag, json_failure=True)
        return resp

    def summary(self) -> dict[str, dict]:
        with self._lock:
            return {k: asdict(v) for k, v in self.totals.items()}

    def reset_totals(self) -> None:
        with self._lock:
            self.totals = {}

    # ----------------------------------------------------------------- private
    @staticmethod
    def cache_key(model: str, messages: list[dict], params: dict) -> str:
        blob = json.dumps({"v": CACHE_VERSION, "model": model, "messages": messages, "params": params},
                          sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _call(self, model: str, messages: list[dict], params: dict, tag: str) -> LLMResponse:
        key = self.cache_key(model, messages, params)
        hit = self.cache.get(key) if self.cache else None
        if hit is not None:
            resp = LLMResponse(text=hit["text"], model=model, usage=Usage(**hit["usage"]),
                               latency_s=hit["latency_s"], cached=True)
        else:
            t0 = time.perf_counter()
            text, usage = self.backend.complete(model, messages, params)
            resp = LLMResponse(text=text, model=model, usage=usage, latency_s=time.perf_counter() - t0)
            if self.cache:
                self.cache.put(key, {"text": text, "usage": asdict(usage), "latency_s": resp.latency_s})
        self._record(tag, key, resp)
        return resp

    @staticmethod
    def _attach_json(resp: LLMResponse) -> None:
        try:
            resp.parsed, resp.parse_error = parse_json_loose(resp.text), None
        except ValueError as e:
            resp.parsed, resp.parse_error = None, str(e)

    def _bump(self, tag: str, resp: LLMResponse | None = None, json_failure: bool = False) -> None:
        with self._lock:
            t = self.totals.setdefault(tag, UsageTotals())
            if json_failure:
                t.json_failures += 1
                return
            assert resp is not None
            t.calls += 1
            t.cached_calls += int(resp.cached)
            t.prompt_tokens += resp.usage.prompt_tokens
            t.completion_tokens += resp.usage.completion_tokens
            t.latency_s += resp.latency_s

    def _record(self, tag: str, key: str, resp: LLMResponse) -> None:
        self._bump(tag, resp)
        if self.log_path:
            line = json.dumps({"ts": time.time(), "tag": tag, "model": resp.model, "key": key[:16],
                               "cached": resp.cached, "prompt_tokens": resp.usage.prompt_tokens,
                               "completion_tokens": resp.usage.completion_tokens,
                               "latency_s": round(resp.latency_s, 3)})
            with self._lock, self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


def gateway_from_config(cfg: dict, cache_dir: str | Path = "cache", log_path: str | Path | None = None) -> Gateway:
    """Build a Gateway from a config block such as

        {"model": "gpt-4o-mini", "base_url": null, "api_key_env": "OPENAI_API_KEY",
         "params": {"temperature": 0}}
    """
    api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    backend = OpenAICompatBackend(base_url=cfg.get("base_url"), api_key=api_key, tpm=cfg.get("tpm"))
    return Gateway(backend, model=cfg["model"], cache_path=Path(cache_dir) / "llm_cache.sqlite",
                   log_path=log_path, default_params=cfg.get("params"))
