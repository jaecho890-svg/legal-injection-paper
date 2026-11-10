"""
cli_backends.py - run models through the user's own signed-in CLIs instead of API keys.

  claude_cli   Claude Code (`claude -p`), signed in to the user's Claude account
  codex_cli    Codex (`codex exec`), signed in to the user's ChatGPT account

Both CLIs are coding agents, so each call is stripped back to a plain chat as far as the
CLI allows. Every flag used is written to the run record, so the paper can state exactly
what the model saw.

Claude: our text replaces the system prompt; every tool, MCP server, slash command,
  hook and CLAUDE.md is disabled (--safe-mode); no session is saved; the process runs from
  an empty folder with a minimal environment. A conversation is one process fed message
  by message over stream-json, so multi-turn runs are real turns.

Codex: runs with a separate CODEX_HOME (LIJ_CODEX_HOME) holding only a login, so your
  ~/.codex/AGENTS.md, memories, plugins and config are not loaded. Our text replaces the
  base instructions (model_instructions_file); optional features are disabled; the sandbox
  is read-only in an empty folder. Codex cannot remove its core tool definitions, so GPT
  runs still see an agent tool list; this residual difference is recorded per call
  (input-token counts) and must be reported in the paper.

Neither CLI accepts a sampling temperature; provider defaults apply and the record says so.
"""
import errno
import json
import os
import pathlib
import re
import subprocess
import tempfile
import time
from typing import List

from .backends import BackendError

RETRYABLE = ("rate limit", "rate_limit", "overloaded", "429", "529", "timeout", "temporarily", "try again",
             "capacity", "reconnecting", "stream disconnected")
# Subscription windows ("You've hit your 5-hour limit · resets 9:20pm (Australia/Sydney)", "usage limit"):
# retrying within the window is pointless, so these stop the whole batch (see runner.run_jobs).
USAGE_LIMIT_RE = re.compile(r"hit your [^.]*limit|usage limit|limit reached|quota exceeded", re.IGNORECASE)


class UsageLimit(BackendError):
    """The subscription's usage window is exhausted. Carries the provider's message (with its reset time)."""


def _clean_env(extra=None) -> dict:
    home = os.environ["HOME"]
    env = {"HOME": home, "USER": os.environ.get("USER", ""), "LANG": "en_US.UTF-8",
           "PATH": f"/usr/bin:/bin:/usr/sbin:/sbin:{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin"}
    # our child CLIs must never auto-update themselves mid-campaign (an update removed the binary for ~90 min once)
    env.update({"DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
    env.update(extra or {})
    return env


def _retrying(fn, attempts=5):
    delay = 30.0
    for i in range(1, attempts + 1):
        try:
            return fn()
        except UsageLimit:
            raise
        except OSError as e:
            # The CLI binary can vanish, or be half-written, while another process
            # updates it: FileNotFoundError, ENOEXEC "Exec format error", ETXTBSY, EACCES.
            # Seen 2026-11-05 19:58 (ENOEXEC), which crashed a whole stage.
            if not isinstance(e, FileNotFoundError) and e.errno not in (errno.ENOEXEC, errno.ETXTBSY, errno.EACCES):
                raise
            if i < attempts:
                time.sleep(120); continue
            raise BackendError(f"CLI binary unavailable: {e}") from None
        except BackendError as e:
            if USAGE_LIMIT_RE.search(str(e)):
                raise UsageLimit(str(e)) from None
            msg = str(e).lower()
            if i < attempts and any(k in msg for k in RETRYABLE):
                time.sleep(delay); delay = min(delay * 2, 900)
                continue
            raise


# ---------------- Claude Code ----------------

def claude_flags(spec, system, params) -> List[str]:
    flags = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
             "--model", spec["model"], "--system-prompt", system or " ",
             "--safe-mode", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
             "--disable-slash-commands", "--no-session-persistence", "--no-chrome"]
    if params.get("effort"):
        flags += ["--effort", params["effort"]]
    return flags


def _claude_conversation(spec, system, turns, params, timeout):
    binary = os.environ.get("LIJ_CLAUDE_BIN", spec.get("binary", "claude"))
    flags = claude_flags(spec, system, params)
    with tempfile.TemporaryDirectory(prefix="lij-claude-") as cwd:
        proc = subprocess.Popen([binary] + flags, cwd=cwd, env=_clean_env(), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        outs, init = [], {}
        try:
            for turn in turns:
                t0 = time.time()
                proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": turn}}) + "\n")
                proc.stdin.flush()
                texts, result = [], None
                deadline = t0 + timeout
                while True:
                    if time.time() > deadline:
                        raise BackendError("timeout waiting for claude reply")
                    line = proc.stdout.readline()
                    if not line:
                        err = proc.stderr.read()[-800:]
                        raise BackendError(f"claude exited early: {err.strip() or 'no output'}")
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "system" and ev.get("subtype") == "init":
                        init = {k: ev.get(k) for k in ("model", "tools", "mcp_servers", "skills", "apiKeySource",
                                                       "claude_code_version", "permissionMode")}
                    elif ev.get("type") == "assistant":
                        texts.append("".join(b.get("text", "") for b in ev["message"].get("content", [])
                                             if b.get("type") == "text"))
                    elif ev.get("type") == "result":
                        result = ev
                        break
                if result.get("is_error"):
                    raise BackendError(f"claude error: {(result.get('result') or ''.join(texts))[:500]}")
                if init.get("tools"):
                    raise BackendError(f"isolation failure: tools exposed {init['tools']}")
                usage = result.get("usage") or {}
                outs.append({"text": result.get("result") or "".join(texts),
                             "returned_model": ",".join(sorted((result.get("modelUsage") or {}).keys())) or init.get("model"),
                             "response_id": result.get("session_id"), "stop_reason": result.get("subtype"),
                             "usage": {k: usage.get(k) for k in ("input_tokens", "output_tokens",
                                                                 "cache_read_input_tokens", "cache_creation_input_tokens")},
                             "latency_s": round(time.time() - t0, 3), "base_url": "claude-cli",
                             "cli": {"binary": binary, "flags": [f if len(f) < 200 else "<system prompt>" for f in flags],
                                     "init": init}})
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
    return outs


# ---------------- Codex ----------------

CODEX_DISABLE = ["apps", "browser_use", "browser_use_external", "computer_use", "goals", "hooks", "image_generation",
                 "in_app_browser", "memories", "plugins", "remote_plugin", "code_mode_host", "multi_agent_v2"]


def codex_home() -> str:
    h = os.environ.get("LIJ_CODEX_HOME")
    if not h:
        raise BackendError("LIJ_CODEX_HOME is not set. Create an isolated Codex login first: "
                           "CODEX_HOME=<folder> codex login   then export LIJ_CODEX_HOME=<folder>")
    if pathlib.Path(h).resolve() == (pathlib.Path.home() / ".codex").resolve():
        raise BackendError("LIJ_CODEX_HOME must not be ~/.codex (it would load your AGENTS.md and memories)")
    if (pathlib.Path(h) / "AGENTS.md").exists():
        raise BackendError(f"{h}/AGENTS.md exists; the isolated Codex home must not contain instructions")
    return h


def codex_flags(spec, params, instr_path, cwd, ephemeral) -> List[str]:
    # `codex exec resume` has no -s / -C, so the sandbox is set by config and the folder by the process cwd
    flags = ["--json", "--ignore-rules", "--skip-git-repo-check", "-m", spec["model"],
             "-c", 'sandbox_mode="read-only"', "-c", "project_doc_max_bytes=0", "-c", f'model_instructions_file="{instr_path}"',
             "-c", 'web_search="disabled"', "-c", 'approval_policy="never"']
    if params.get("effort"):
        flags += ["-c", f'model_reasoning_effort="{params["effort"]}"']
    for f in CODEX_DISABLE:
        flags += ["--disable", f]
    if ephemeral:
        flags.append("--ephemeral")
    return flags


def _codex_conversation(spec, system, turns, params, timeout):
    home = codex_home()
    binary = os.environ.get("LIJ_CODEX_BIN", spec.get("binary", "codex"))
    outs, thread = [], None
    with tempfile.TemporaryDirectory(prefix="lij-codex-") as tmp:
        cwd = os.path.join(tmp, "work"); os.mkdir(cwd)
        instr = os.path.join(tmp, "instructions.md")
        pathlib.Path(instr).write_text(system or " ")
        ephemeral = len(turns) == 1
        for i, turn in enumerate(turns):
            flags = codex_flags(spec, params, instr, cwd, ephemeral)
            cmd = [binary, "exec"] + (["resume"] if i > 0 else []) + flags + ([thread] if i > 0 else []) + ["-"]
            t0 = time.time()
            try:
                r = subprocess.run(cmd, cwd=cwd, env=_clean_env({"CODEX_HOME": home}), input=turn,
                                   capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise BackendError("timeout waiting for codex reply")
            texts, usage, failed = [], None, None
            for line in r.stdout.splitlines():
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = ev.get("type")
                if t == "thread.started":
                    thread = thread or ev.get("thread_id")
                elif t == "item.completed" and ev.get("item", {}).get("type") == "agent_message":
                    texts.append(ev["item"].get("text", ""))
                elif t == "item.completed" and ev.get("item", {}).get("type") in ("command_execution", "mcp_tool_call",
                                                                                   "web_search", "file_change"):
                    failed = f"model used a tool ({ev['item']['type']}); run discarded"
                elif t == "turn.completed":
                    usage = ev.get("usage")
                elif t in ("turn.failed", "error"):
                    failed = json.dumps(ev)[:500]
            if failed or not texts:
                raise BackendError(f"codex: {failed or (r.stderr[-500:].strip() or 'no reply')}")
            outs.append({"text": texts[-1], "returned_model": spec["model"], "response_id": thread,
                         "stop_reason": "turn.completed", "usage": usage, "latency_s": round(time.time() - t0, 3),
                         "base_url": "codex-cli",
                         "cli": {"binary": binary, "flags": flags, "codex_home": "isolated",
                                 "note": "returned_model not reported by codex; requested id recorded"}})
            if i == 0 and not thread and len(turns) > 1:
                raise BackendError("codex did not report a thread id; cannot continue the conversation")
    return outs


def converse(spec, system, turns, params, timeout=900):
    if spec["provider"] == "claude_cli":
        return _retrying(lambda: _claude_conversation(spec, system, turns, params, timeout))
    if spec["provider"] == "codex_cli":
        return _retrying(lambda: _codex_conversation(spec, system, turns, params, timeout))
    raise BackendError(f"not a CLI provider: {spec['provider']}")
