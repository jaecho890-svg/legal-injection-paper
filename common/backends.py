"""
backends.py - direct model API calls, standard library only (Python 3.9+).

Every call goes straight to the provider's public API with an explicitly pinned
model id and explicit sampling parameters. Nothing routes through Claude Code
subagents or a local proxy, so the request the paper describes is exactly the
request that was sent.

Providers
  anthropic      POST https://api.anthropic.com/v1/messages
  openai         POST https://api.openai.com/v1/chat/completions
  openai_compat  any OpenAI-compatible endpoint (Gemini's OpenAI endpoint,
                 OpenRouter, Together, vLLM, Ollama ...) via base_url in models.json
  mock           deterministic offline responses for testing the pipeline

Base URLs are taken from models.json only. ANTHROPIC_BASE_URL / OPENAI_BASE_URL
in the environment are deliberately ignored: they often point at local proxies,
which would silently change which model answers.
"""
import http.client
import json
import socket
import os
import random
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

DEFAULT_BASES = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
}
ANTHROPIC_VERSION = "2023-06-01"
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class BackendError(RuntimeError):
    pass


def _post(url: str, headers: Dict[str, str], body: dict, timeout: float) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _with_retries(fn, max_attempts: int = 6):
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            if e.code in RETRY_STATUS and attempt < max_attempts:
                retry_after = e.headers.get("retry-after")
                wait = float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() else delay
                time.sleep(wait + random.uniform(0, 1))
                delay = min(delay * 2, 60)
                continue
            raise BackendError(f"HTTP {e.code}: {detail}") from None
        # socket.timeout is not a TimeoutError before Python 3.10; a slow read crashed whole runs (2026-11-08)
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, http.client.IncompleteRead) as e:
            if attempt < max_attempts:
                time.sleep(delay + random.uniform(0, 1))
                delay = min(delay * 2, 60)
                continue
            raise BackendError(f"network error: {e}") from None


def _key(spec: dict) -> str:
    env = spec.get("key_env")
    if not env:
        return ""
    val = os.environ.get(env, "")
    if not val:
        raise BackendError(f"environment variable {env} is not set (needed for model '{spec['alias']}')")
    return val


def call(spec: dict, system: str, messages: List[dict], params: dict,
         mock_hint: Optional[str] = None, timeout: float = 600) -> dict:
    """Send one request. `messages` is a list of {"role": "user"|"assistant", "content": str}.

    Returns {text, returned_model, response_id, stop_reason, usage, latency_s, base_url}.
    """
    provider = spec["provider"]
    t0 = time.time()
    if provider == "mock":
        from . import mock
        out = mock.respond(spec, system, messages, params, mock_hint)
        out.update({"latency_s": 0.0, "base_url": "mock://"})
        return out

    if provider == "anthropic":
        base = spec.get("base_url") or DEFAULT_BASES["anthropic"]
        body = {"model": spec["model"], "system": system, "messages": messages,
                "max_tokens": params["max_tokens"]}
        if params.get("temperature") is not None and spec.get("supports_temperature", True):
            body["temperature"] = params["temperature"]
        headers = {"x-api-key": _key(spec), "anthropic-version": ANTHROPIC_VERSION}
        r = _with_retries(lambda: _post(base.rstrip("/") + "/v1/messages", headers, body, timeout))
        text = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
        return {"text": text, "returned_model": r.get("model"), "response_id": r.get("id"),
                "stop_reason": r.get("stop_reason"), "usage": r.get("usage"),
                "latency_s": round(time.time() - t0, 3), "base_url": base}

    if provider in ("openai", "openai_compat"):
        base = spec.get("base_url") or DEFAULT_BASES.get(provider)
        if not base:
            raise BackendError(f"model '{spec['alias']}' needs base_url in models.json")
        msgs = ([{"role": spec.get("system_role", "system"), "content": system}] if system else []) + messages
        body = {"model": spec["model"], "messages": msgs,
                spec.get("max_tokens_param", "max_completion_tokens"): params["max_tokens"]}
        if params.get("temperature") is not None and spec.get("supports_temperature", True):
            body["temperature"] = params["temperature"]
        if params.get("seed") is not None and spec.get("supports_seed", False):
            body["seed"] = params["seed"]
        body.update(spec.get("extra_body", {}))
        key = _key(spec)
        headers = {"authorization": f"Bearer {key}"} if key else {}
        r = _with_retries(lambda: _post(base.rstrip("/") + "/chat/completions", headers, body, timeout))
        choice = (r.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        return {"text": text, "returned_model": r.get("model"), "response_id": r.get("id"),
                "stop_reason": choice.get("finish_reason"), "usage": r.get("usage"),
                "system_fingerprint": r.get("system_fingerprint"),
                "latency_s": round(time.time() - t0, 3), "base_url": base}

    raise BackendError(f"unknown provider '{provider}'")
