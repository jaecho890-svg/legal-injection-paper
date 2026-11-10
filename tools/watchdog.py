#!/usr/bin/env python3
"""
watchdog.py - exit (printing why) when a campaign queue finishes, dies, or stalls outside a wait.

Every check is appended to campaign_logs/watchdog.log, so the log shows each queue's
state every five minutes for the whole campaign.

  python3 tools/watchdog.py claude gpt
"""
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / "campaign_logs" / "watchdog.log"
STALE_MIN = 90
EVERY_S = 300
CLAUDE_RE = re.compile(r"^(fable|opus|haiku|sonnet)-")


def alive(q):
    r = subprocess.run(["pgrep", "-f", f"campaign.py --queue {q}$"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def newest(q):
    """mtime of the newest result file this queue wrote (judge files count for gpt)."""
    best = 0
    for d in ROOT.glob("*/results_v2/*"):
        sub = d.name
        if sub == "analysis" or not d.is_dir():
            continue
        for f in os.scandir(d):
            n = f.name
            if q.startswith("gpt"):
                ok = n.startswith("gpt-") or sub.startswith("judge_gpt")
            elif q.startswith("claude"):
                ok = bool(CLAUDE_RE.match(n)) and not sub.startswith("judge_")
            else:
                ok = True
            if ok:
                best = max(best, f.stat().st_mtime)
    return best


def last_line(q):
    try:
        lines = (ROOT / "campaign_logs" / f"{q}.log").read_text().splitlines()
        return lines[-1] if lines else ""
    except OSError:
        return ""


def record(msg):
    line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}"
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")
    return line


def main(queues):
    record(f"watchdog start: {', '.join(queues)}")
    while True:
        states = []
        for q in queues:
            line = last_line(q)
            age = (time.time() - newest(q)) / 60
            waiting = "USAGE LIMIT" in line or "pausing" in line
            if f"QUEUE {q} FINISHED" in line:
                print(record(f"{q}: FINISHED")); return
            if not alive(q):
                print(record(f"{q}: DEAD (no campaign process); last log line: {line[:300]}")); return
            if not waiting and age > STALE_MIN:
                print(record(f"{q}: STALE newest result {age:.0f} min ago; last log line: {line[:300]}")); return
            states.append(f"{q} {'WAITING' if waiting else 'OK'} newest {age:.0f}m")
        record(" | ".join(states))
        time.sleep(EVERY_S)


if __name__ == "__main__":
    main(sys.argv[1:] or ["claude", "gpt"])
