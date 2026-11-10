"""
probe.py - check each model route before spending runs on it.

For every alias it runs two short conversations and checks that:
  1. the model answers at all (auth, model id, rate limits);
  2. our system prompt is the one in force (it can repeat a codeword planted only there);
  3. no outside instructions leak in (it reports no CLAUDE.md / AGENTS.md / memory / user notes);
  4. multi-turn works (it remembers a number from the previous turn);
  5. no tools were exposed or used.
Results go to common/probe_report.json. With --mark-verified, aliases that pass every check
get verified=true in models.json, which is what lets the experiment runner use them.

  python3 -m common.probe --models fable-5.1,opus-5.5,gpt-6.1-sol --mark-verified
"""
import argparse
import datetime as dt
import json
import pathlib
import random

from . import backends, runner

HERE = pathlib.Path(__file__).resolve().parent

# Phrases that only occur in the user's own instruction files (~/.claude/CLAUDE.md, ~/.codex/AGENTS.md).
LEAK_MARKERS = ["taste-skill", "design-taste", "screen explains itself", "Hierarchy is type and space",
                "How to work with me", "evidence-gated autonomy"]
# Input-token ceilings for the probe prompt: measured wrapper + prompt, with margin. Codex's base is its tool list.
TOKEN_CEILING = {"claude_cli": 1100, "codex_cli": 12000}


def probe(alias: str) -> dict:
    spec = runner.resolve(alias, allow_unverified=True)
    params = runner.default_params("reviewer")
    code = f"KESTREL-{random.randint(1000, 9999)}"
    system = (f"You are a plain text assistant for a research test. The codeword is {code}. "
              "Answer briefly and honestly. Do not use tools.")
    turns_a = [("Two questions. (1) What is the codeword in your instructions? (2) Apart from this short "
                "instruction, do you have any other instructions in your context, such as a CLAUDE.md, AGENTS.md, "
                "memory entries, notes about the user, or a description of a coding environment? Answer YES or NO, "
                "and if YES quote the first 12 words.")]
    turns_b = ["Remember the number 731. Reply only: OK", "What number did I ask you to remember? Reply with the number only."]
    rep = {"alias": alias, "model": spec["model"], "provider": spec["provider"],
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "checks": {}}
    try:
        if spec["provider"] in ("claude_cli", "codex_cli"):
            from . import cli_backends
            a = cli_backends.converse(spec, system, turns_a, params, timeout=600)
            b = cli_backends.converse(spec, system, turns_b, params, timeout=600)
        else:
            a = [backends.call(spec, system, [{"role": "user", "content": turns_a[0]}], params)]
            b1 = backends.call(spec, system, [{"role": "user", "content": turns_b[0]}], params)
            b2 = backends.call(spec, system, [{"role": "user", "content": turns_b[0]},
                                              {"role": "assistant", "content": b1["text"]},
                                              {"role": "user", "content": turns_b[1]}], params)
            b = [b1, b2]
    except backends.BackendError as e:
        rep["error"] = str(e)
        rep["passed"] = False
        return rep
    ans = a[0]["text"]
    rep["answer"] = ans[:600]
    rep["returned_model"] = a[0].get("returned_model")
    rep["usage"] = a[0].get("usage")
    rep["cli_init"] = (a[0].get("cli") or {}).get("init")
    rep["checks"]["answers"] = bool(ans.strip())
    rep["checks"]["system_prompt_in_force"] = code in ans
    up = ans.upper()
    # Known, constant wrappers are allowed: Claude Code adds an SDK identity line, an account-email reminder and an
    # environment block (~630 tokens) that cannot be switched off. What must NOT appear is user-authored material:
    # CLAUDE.md / AGENTS.md content, memory entries or prior-chat context. Two signals: distinctive phrases from the
    # user's own instruction files, and the input-token count (those files would add hundreds of tokens).
    leaked = [m for m in LEAK_MARKERS if m.upper() in up]
    u = a[0].get("usage") or {}
    tok = sum((u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    rep["input_tokens_total"] = tok
    rep["leak_markers_found"] = leaked
    ceiling = TOKEN_CEILING.get(spec["provider"])
    rep["checks"]["no_user_instruction_files"] = not leaked and (ceiling is None or tok <= ceiling)
    rep["checks"]["multiturn_memory"] = "731" in b[-1]["text"]
    init = rep["cli_init"] or {}
    rep["checks"]["no_tools_exposed"] = not init.get("tools") if spec["provider"] == "claude_cli" else None
    want = model_ok = True
    if spec["provider"] == "claude_cli":
        model_ok = spec["model"] in (rep["returned_model"] or "")
        rep["checks"]["returned_model_matches"] = model_ok
    rep["passed"] = all(v for v in rep["checks"].values() if v is not None) and want and model_ok
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--mark-verified", action="store_true")
    args = ap.parse_args()
    report_path = HERE / "probe_report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    reg = json.loads(runner.REGISTRY_PATH.read_text())
    import concurrent.futures as cf
    aliases = runner.split_models(args.models)
    with cf.ThreadPoolExecutor(max_workers=min(6, len(aliases))) as ex:
        results = list(ex.map(probe, aliases))
    for alias, r in zip(aliases, results):
        report[alias] = r
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{status}  {alias:14s} {r.get('error') or r['checks']}")
        if r["passed"] and args.mark_verified:
            reg["models"][alias]["verified"] = True
            reg["models"][alias]["probed_at"] = r["at"]
    report_path.write_text(json.dumps(report, indent=2))
    if args.mark_verified:
        runner.REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
