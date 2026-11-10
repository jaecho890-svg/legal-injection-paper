# What each model actually sees

The paper must say what context each model received beyond our prompt. This page records it per route, as established by `common/probe.py` on 2026-11-04. Re-run the probe after any CLI update.

## Claude models: Claude Code CLI (`claude_cli`)

Flags on every call (also stored in each run record under `exchanges[].cli`):

```
claude -p --input-format stream-json --output-format stream-json --verbose
       --model <id> --system-prompt <our system prompt> --effort <level>
       --safe-mode --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}'
       --disable-slash-commands --no-session-persistence --no-chrome
```

Each call runs from a fresh empty temporary folder with a minimal environment (`HOME`, `USER`, `LANG`, `PATH`).

**Removed:** Claude Code's default system prompt, all tools, MCP servers, skills, slash commands, hooks, CLAUDE.md files (including `~/.claude/CLAUDE.md`), auto-memory, and session history. The probe confirms that no tools are exposed, that our system prompt is in force, and that no text from the user's instruction files appears.

**Not removable (constant across all conditions):** about 630 tokens that Claude Code always adds:

1. an identity line placed before our system prompt: "You are a Claude agent, built on Anthropic's Claude Agent SDK."
2. a reminder containing the signed-in account's email address, with a note on when it may be used
3. an environment block: the temporary working folder, platform, shell, model name, today's date, and guidance on treating downloaded files as untrusted

None of the environment-variable switches we tested remove these: `CLAUDE_CODE_DISABLE_ATTACHMENTS`, `..._CLAUDE_MDS`, `..._AUTO_MEMORY`, `..._GIT_INSTRUCTIONS`, `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT`, and an empty `CLAUDE_CODE_USER_EMAIL`. `--bare` would remove them, but it requires an API key and cannot use a subscription login.

*Paper wording:* Claude models were accessed through Claude Code with its default system prompt replaced and all tools and user configuration disabled. A fixed wrapper of about 630 tokens (an agent identity line, an account-email notice and an environment description) was present in every call, identically across conditions.

**The wrapper is read, not ignored.** In 4 outputs, all from Fable 5.1 (2 of the ~1,700 first Claude Kestrel reviews on 2026-11-05, and later 2 DD summaries), the model copied the account email from item 2 into its header ("Prepared for: Wattlebridge Holdings deal team (<account email>)"). Reviews also date themselves from item 3. Neither changes a coded conclusion, but the paper should say the wrapper is visible to the model, and the raw records hold the signed-in address. In a further 8 Fable 5.1 outputs the model turned that address into a name and put the name in its memo header. The records stay unedited in the private working repository. The public copy is built by `tools/export_public.py`, which replaces every email address except in the README, paper and export tool, every home-folder path, and that name (with the author's published name), lists each changed file in `REDACTION_REPORT.json`, then re-scans the export. Recount with `grep -rl "@gmail" */results_v2`.

**Sampling:** temperature cannot be set and the provider default applies. Effort is set explicitly (default `medium`, see `common/models.json`). The harness's `max_tokens` setting is not enforced on this route: Kestrel reviews ran to 6,000–7,500 output tokens.

## GPT models: Codex CLI (`codex_cli`)

Runs with `CODEX_HOME=$LIJ_CODEX_HOME`, a separate folder containing only a Codex login, so `~/.codex/AGENTS.md`, memories, plugins and config are never loaded. The harness refuses to run if that folder is `~/.codex` or contains an `AGENTS.md`.

```
codex exec --json --ignore-rules --skip-git-repo-check -m <id>
     -c sandbox_mode="read-only" -c project_doc_max_bytes=0
     -c model_instructions_file="<file holding our system prompt>"
     -c web_search="disabled" -c approval_policy="never" -c model_reasoning_effort="<level>"
     --disable apps --disable browser_use --disable browser_use_external --disable computer_use
     --disable goals --disable hooks --disable image_generation --disable in_app_browser
     --disable memories --disable plugins --disable remote_plugin --disable code_mode_host
     --disable multi_agent_v2  [--ephemeral for single-turn]
```

Multi-turn conversations use `codex exec resume <thread>`.

**Not removable:** Codex's core agent tool definitions (shell execution and a few others) remain in context. With isolation, the two-line probe prompt still used 5,200–7,400 input tokens depending on the model (measured 2026-11-04), almost all of it Codex's own instructions and tool definitions. Any run in which the model *used* a tool is discarded and recorded as an error. Codex does not report the model version it actually served, so records hold the requested id.

*Paper wording:* GPT models were accessed through the Codex CLI with its base instructions replaced, user configuration excluded and optional features disabled. Codex's core tool definitions could not be removed and were present in every call; no run in which a tool was invoked was retained.

## API models: Gemini, OpenRouter (`openai_compat`)

Direct HTTPS calls. Only our system prompt and messages are sent, with explicit temperature. These are the cleanest routes but have tiny free quotas.

## Consequences for the analysis

- Every comparison in the paper is **within a model and route**: a condition against its own clean control. The constant wrappers above cancel out of those differences.
- **Cross-route** comparisons of absolute levels (for example, Claude's baseline against Gemini's) carry the wrapper difference and must be described with that caveat.
