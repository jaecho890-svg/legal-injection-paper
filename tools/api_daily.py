#!/usr/bin/env python3
"""
api_daily.py - grow the API-model Kestrel subset to 20 reps inside the free daily quotas.

Each run adds as many replicates as today's quota allows (Gemini about 20 requests a day,
OpenRouter about 50 shared by its three models), judges the new reviews with GPT-6.1 Sol and
re-runs the Kestrel analysis. Rate-limited calls stay as error records and are retried the next
day. Once every model has 20 ok reviews per cell it does nothing.

Run by launchd daily at 20:00 (after Gemini's and OpenRouter's daily resets in AEDT):
  ~/Library/LaunchAgents/com.jaecho.legal-injection.api-daily.plist
By hand:  python3 tools/api_daily.py [--gemini 18] [--openrouter 48]
Keys: read from LIJ_ENV_FILE (default ~/.config/legal-injection/api.env), never printed.
Log: campaign_logs/api_daily.log
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
K = ROOT / "kestrel-injection-study"
LOG = ROOT / "campaign_logs" / "api_daily.log"
CELLS = ["C0", "A2", "B3"]          # task OPEN, guard GUARD_OFF
TARGET = 20
GROUPS = {"gemini": ["gemini"], "openrouter": ["nemotron-3-ultra", "dots-3-note", "xing-4.0"]}


def log(msg):
    line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def load_env():
    path = pathlib.Path(os.environ.get("LIJ_ENV_FILE", pathlib.Path.home() / ".config/legal-injection/api.env"))
    env = dict(os.environ)
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.removeprefix("export ").split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    env.setdefault("LIJ_CODEX_HOME", str(pathlib.Path.home() / ".codex-research"))
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "/usr/bin:/bin")
    return env


def ok_reps(model):
    """{cell: set of rep numbers with an ok review}"""
    out = {c: set() for c in CELLS}
    for c in CELLS:
        for f in (K / "results_v2" / "reviewer").glob(f"{model}__{c}__OPEN__GUARD_OFF__r*.json"):
            try:
                if json.loads(f.read_text()).get("status") == "ok":
                    out[c].add(int(f.stem.rsplit("__r", 1)[1]))
            except (ValueError, OSError):
                pass
    return out


def plan(model, budget):
    """Largest rep target whose missing calls fit the budget."""
    have = ok_reps(model)
    best = None
    for reps in range(1, TARGET + 1):
        need = sum(len(set(range(1, reps + 1)) - have[c]) for c in CELLS)
        if need <= budget:
            best = (reps, need)
    return best


def run(cmd, env):
    r = subprocess.run([sys.executable] + cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("done:") or "jobs," in l]
    return r.returncode, " | ".join(tail)[-300:], r.stderr[-300:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemini", type=int, default=18, help="calls to spend on Gemini today")
    ap.add_argument("--openrouter", type=int, default=48, help="calls to spend on OpenRouter today, split evenly")
    a = ap.parse_args()
    env = load_env()
    budgets = {"gemini": a.gemini, "openrouter": a.openrouter}
    ran = False
    for group, models in GROUPS.items():
        per = budgets[group] // len(models)
        for m in models:
            p = plan(m, per)
            have = ok_reps(m)
            done = min(len(v) for v in have.values())
            if done >= TARGET:
                log(f"{m}: complete ({TARGET} reps per cell)")
                continue
            if not p or p[1] == 0:
                log(f"{m}: nothing fits today's budget of {per}")
                continue
            reps, need = p
            rc, out, err = run(["kestrel-injection-study/harness/experiment.py", "run", "--models", m,
                                "--conditions", ",".join(CELLS), "--tasks", "OPEN", "--guards", "GUARD_OFF",
                                "--reps", str(reps), "--workers", "1", "--max-calls", str(per)], env)
            log(f"{m}: reps -> {reps} ({need} calls) rc={rc} {out} {err if rc else ''}")
            ran = True
    if ran:
        rc, out, err = run(["kestrel-injection-study/harness/experiment.py", "judge", "--judge", "gpt-6.1-sol",
                            "--workers", "4"], env)
        log(f"judge: rc={rc} {out} {err if rc else ''}")
        rc, out, err = run(["kestrel-injection-study/harness/experiment.py", "analyze"], env)
        log(f"analyze: rc={rc} {err if rc else ''}")


if __name__ == "__main__":
    main()
