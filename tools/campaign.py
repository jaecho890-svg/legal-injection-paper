#!/usr/bin/env python3
"""
campaign.py - run the agreed experiment plan as a queue of stages, one queue per route.

Plan "core-five" (agreed 2026-11-04):
  core models, 20 reps, all four studies on the pilot (non-draft) cases
      Claude: fable-5.1, opus-5.5, haiku-5.5      GPT: gpt-6.1-sol, gpt-6-luna
  breadth models, 5 reps, Kestrel + drift only
      Claude: sonnet-5.5, opus-4.8                GPT: the other six GPT models
  draft-case pilots, 3 reps, control / honest arms only (balance checks before legal review)
  pipelines stay within a vendor: cheap parser -> strong orchestrators
  Fable 5.1 capped at 10 reps (--model-reps) to fit the Claude usage window
  judge: GPT-6.1 Sol codes everything (GPT queue passes + a judge-final catch-up pass);
         Opus 5.5 codes a deterministic 10% sample in judge-final, for inter-judge agreement
  usage windows: a stage that reports "USAGE LIMIT HIT" sleeps until the stated reset time and resumes

Each stage is the study's own CLI command. A stage is re-run (resuming, so only failed
jobs repeat) while it still has errors, with a pause between passes so subscription rate
limits can reset. Progress goes to campaign_logs/<queue>.log and campaign_logs/<queue>.status.json;
the full output of every stage pass goes to campaign_logs/stages/<queue>/.

  python3 tools/campaign.py --queue claude [--dry-run]
  python3 tools/campaign.py --queue gpt    [--dry-run]
  python3 tools/campaign.py --queue judge-final
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS = ROOT / "campaign_logs"
K = "kestrel-injection-study/harness/experiment.py"
D = "interpretive-drift-study/harness/experiment.py"
I = "ip-assignment-study/harness/experiment.py"
P = "dd-pipeline-study/harness/experiment.py"
DD_CORPORA = ["overt", "subtle", "mechanism", "discovery"]


FABLE_CAP = ["--model-reps", "fable-5.1=10"]   # agreed 2026-11-04: Fable at 10 reps to fit the Claude usage window



def wall_sleep(seconds):
    """Sleep until a wall-clock deadline. time.sleep stops counting while macOS
    is asleep (lid shut, flat battery), which would stretch a usage-limit wait
    by however long the machine slept; this polls the real clock instead."""
    deadline = time.time() + seconds
    while True:
        left = deadline - time.time()
        if left <= 0:
            return
        time.sleep(min(left, 60))

def queue_claude():
    core, w = "fable-5.1,opus-5.5,haiku-5.5", "4"
    s = [("kestrel core", [K, "run", "--models", core, "--reps", "20", "--workers", w] + FABLE_CAP),
         ("drift core", [D, "run", "--models", core, "--reps", "20", "--workers", w] + FABLE_CAP),
         ("ip core", [I, "run", "--models", core, "--reps", "20", "--workers", w] + FABLE_CAP),
         ("ip pipeline", [I, "pipeline", "--parser", "haiku-5.5", "--models", "opus-5.5,fable-5.1", "--reps", "20",
                          "--workers", w] + FABLE_CAP)]
    s += [(f"dd {c}", [P, "run", "--corpus", c, "--parsers", "haiku-5.5", "--models", "opus-5.5,fable-5.1",
                       "--reps", "20", "--workers", w] + FABLE_CAP) for c in DD_CORPORA]
    s += [("kestrel breadth", [K, "run", "--models", "sonnet-5.5,opus-4.8", "--reps", "5", "--workers", w]),
          ("drift breadth", [D, "run", "--models", "sonnet-5.5,opus-4.8", "--reps", "5", "--workers", w]),
          ("draft pilot: employment", [D, "run", "--case", "case_employment.json", "--arms", "control",
                                       "--models", "opus-5.5,haiku-5.5", "--reps", "3", "--workers", w]),
          ("draft pilot: insurance", [D, "run", "--case", "case_insurance.json", "--arms", "control",
                                      "--models", "opus-5.5,haiku-5.5", "--reps", "3", "--workers", w]),
          ("draft pilot: ip executed", [I, "run", "--case", "case_executed.json", "--arms", "honest",
                                        "--models", "opus-5.5,haiku-5.5", "--reps", "3", "--workers", w])]
    # no judging here: the primary judge is GPT-6.1 Sol (GPT queue); Opus 5.5 judges a 10% sample in judge-final
    return s


def queue_gpt():
    core, w = "gpt-6.1-sol,gpt-6-luna", "6"
    breadth = "gpt-6.1-terra,gpt-6-astra,gpt-6-sol,gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna"
    s = [("kestrel core", [K, "run", "--models", core, "--reps", "20", "--workers", w]),
         ("kestrel judge (pass 1)", [K, "judge", "--judge", "gpt-6.1-sol", "--workers", w]),
         ("drift core", [D, "run", "--models", core, "--reps", "20", "--workers", w]),
         ("ip core", [I, "run", "--models", core, "--reps", "20", "--workers", w]),
         ("ip pipeline", [I, "pipeline", "--parser", "gpt-6-luna", "--models", "gpt-6.1-sol", "--reps", "20", "--workers", w])]
    s += [(f"dd {c}", [P, "run", "--corpus", c, "--parsers", "gpt-6-luna", "--models", "gpt-6.1-sol",
                       "--reps", "20", "--workers", w]) for c in DD_CORPORA]
    s += [("dd judge (pass 1)", [P, "judge", "--judge", "gpt-6.1-sol", "--workers", w]),
          ("kestrel breadth", [K, "run", "--models", breadth, "--reps", "5", "--workers", w]),
          ("drift breadth", [D, "run", "--models", breadth, "--reps", "5", "--workers", w]),
          ("draft pilot: employment", [D, "run", "--case", "case_employment.json", "--arms", "control",
                                       "--models", core, "--reps", "3", "--workers", w]),
          ("draft pilot: insurance", [D, "run", "--case", "case_insurance.json", "--arms", "control",
                                      "--models", core, "--reps", "3", "--workers", w]),
          ("draft pilot: ip executed", [I, "run", "--case", "case_executed.json", "--arms", "honest",
                                        "--models", core, "--reps", "3", "--workers", w]),
          ("kestrel judge (pass 2)", [K, "judge", "--judge", "gpt-6.1-sol", "--workers", w]),
          ("dd judge (pass 2)", [P, "judge", "--judge", "gpt-6.1-sol", "--workers", w])]
    return s


def queue_judge_final():
    """Run after BOTH collection queues finish."""
    return [("kestrel judge gpt (final)", [K, "judge", "--judge", "gpt-6.1-sol", "--workers", "6"]),
            ("dd judge gpt (final)", [P, "judge", "--judge", "gpt-6.1-sol", "--workers", "6"]),
            ("kestrel judge opus 10%", [K, "judge", "--judge", "opus-5.5", "--sample", "0.1", "--workers", "4"]),
            ("dd judge opus 10%", [P, "judge", "--judge", "opus-5.5", "--sample", "0.1", "--workers", "4"]),
            ("kestrel judge agreement", [K, "agreement", "--a", "gpt-6.1-sol", "--b", "opus-5.5"]),
            ("dd judge agreement", [P, "agreement", "--a", "gpt-6.1-sol", "--b", "opus-5.5"]),
            ("kestrel analyze", [K, "analyze"]), ("drift analyze", [D, "analyze"]),
            ("ip analyze", [I, "analyze"]), ("dd analyze", [P, "analyze"])]


def _phase2(core, w, parser, orchs, breadth, cap):
    """Phase 2 (2026-11-06): the backlog items that need no legal sign-off to run. Cheap and novel first."""
    return [
        ("p2 dd loneflag", [P, "run", "--corpus", "loneflag", "--parsers", parser, "--models", orchs,
                            "--reps", "20", "--workers", w] + cap),
        ("p2 drift last-position (core)", [D, "run", "--arms", "lastA,lastB", "--models", core, "--reps", "20",
                                           "--workers", w] + cap),
        ("p2 drift last-position (breadth)", [D, "run", "--arms", "lastA,lastB", "--models", breadth, "--reps", "5",
                                              "--workers", w]),
        ("p2 kestrel pdf", [K, "run", "--conditions", "C0P,A2P", "--tasks", "OPEN", "--models", core, "--reps", "20",
                            "--workers", w] + cap),
        ("p2 ip executed (positive control)", [I, "run", "--case", "case_executed.json", "--models", core,
                                               "--reps", "20", "--workers", w] + cap),
        ("p2 drift employment", [D, "run", "--case", "case_employment.json", "--models", core, "--reps", "20",
                                 "--workers", w] + cap),
        ("p2 drift insurance", [D, "run", "--case", "case_insurance.json", "--models", core, "--reps", "20",
                                "--workers", w] + cap),
    ]


def queue_claude2():
    return _phase2("fable-5.1,opus-5.5,haiku-5.5", "4", "haiku-5.5", "opus-5.5,fable-5.1", "sonnet-5.5,opus-4.8", FABLE_CAP)


def queue_gpt2():
    w = "6"
    s = _phase2("gpt-6.1-sol,gpt-6-luna", w, "gpt-6-luna", "gpt-6.1-sol",
                "gpt-6.1-terra,gpt-6-astra,gpt-6-sol,gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna", [])
    # the GPT judge codes the GPT side as it lands; judge-final2 catches up the Claude side
    return s + [("p2 kestrel judge", [K, "judge", "--judge", "gpt-6.1-sol", "--workers", w]),
                ("p2 dd judge", [P, "judge", "--judge", "gpt-6.1-sol", "--workers", w])]


def queue_judge_final2():
    """Run after BOTH phase-2 queues finish. The Opus sample is deterministic by run id, so runs it
    already coded are skipped and only new runs can fall into the 10%."""
    return [(n.replace("(final)", "(final 2)"), c) for n, c in queue_judge_final()]


GLOSS_ARMS = "glossA,glossB,dripA,dripB,strongA,strongB,strongA_poorsep"


def _gloss_rerun(core, w, cap):
    """After the 2026-11-08 legal review (docs/FIXTURE_REVIEW_2026-11-08.md): only the arms that read glosses."""
    return [(f"review rerun: {c} gloss arms", [D, "run", "--case", f"case_{c}.json", "--arms", GLOSS_ARMS,
                                               "--models", core, "--reps", "20", "--workers", w] + cap)
            for c in ("employment", "insurance")] + [("review rerun: drift analyze", [D, "analyze"])]


def queue_review_claude():
    return _gloss_rerun("fable-5.1,opus-5.5,haiku-5.5", "4", FABLE_CAP)


def queue_review_gpt():
    return _gloss_rerun("gpt-6.1-sol,gpt-6-luna", "6", [])


QUEUES = {"claude": queue_claude, "gpt": queue_gpt, "judge-final": queue_judge_final,
          "claude2": queue_claude2, "gpt2": queue_gpt2, "judge-final2": queue_judge_final2,
          "review-claude": queue_review_claude, "review-gpt": queue_review_gpt}
DONE_RE = re.compile(r"done: (\d+) ok, (\d+) errors")
LIMIT_RE = re.compile(r"USAGE LIMIT HIT: (.*)")
RESET_RE = re.compile(r"resets\s+(?:(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}),?\s+)?(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)"
                      r"(?:\s*\((?P<tz>[^)]+)\))?", re.IGNORECASE)


def seconds_until_reset(msg, now_ts=None, fallback=1800, margin=300):
    """Parse 'resets 9:20pm (Australia/Sydney)' or 'resets Nov 6, 9am (...)' -> seconds to wait (plus margin)."""
    m = RESET_RE.search(msg or "")
    if not m:
        return fallback
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(m.group("tz")) if m.group("tz") else None
    except Exception:
        tz = None
    now_dt = dt.datetime.fromtimestamp(now_ts or time.time(), tz=tz) if tz else dt.datetime.fromtimestamp(now_ts or time.time())
    h = int(m.group("h")) % 12 + (12 if m.group("ap").lower() == "pm" else 0)
    target = now_dt.replace(hour=h, minute=int(m.group("m") or 0), second=0, microsecond=0)
    if m.group("mon"):
        mon = dt.datetime.strptime(m.group("mon"), "%b").month
        target = target.replace(month=mon, day=int(m.group("day")))
        if target < now_dt - dt.timedelta(days=1):
            target = target.replace(year=target.year + 1)
    elif target <= now_dt:
        target += dt.timedelta(days=1)
    return max(60, int((target - now_dt).total_seconds()) + margin)


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True, choices=list(QUEUES))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-passes", type=int, default=8)
    ap.add_argument("--pause-min", type=float, default=20, help="minutes to wait before re-running a stage with errors")
    a = ap.parse_args()
    LOGS.mkdir(exist_ok=True)
    log = (LOGS / f"{a.queue}{'-dry' if a.dry_run else ''}.log").open("a")
    status_path = LOGS / f"{a.queue}{'-dry' if a.dry_run else ''}.status.json"
    env = dict(os.environ)
    if a.queue in ("gpt", "judge-final"):
        env.setdefault("LIJ_CODEX_HOME", str(pathlib.Path.home() / ".codex-research"))
    stages = QUEUES[a.queue]()
    status = {"queue": a.queue, "started": now(), "stages": []}

    def write(msg):
        line = f"[{now()}] {msg}"
        print(line, flush=True); log.write(line + "\n"); log.flush()

    for name, cmd in stages:
        args = [sys.executable] + cmd + (["--dry-run"] if a.dry_run and cmd[1] in ("run", "judge", "pipeline") else [])
        st = {"stage": name, "started": now(), "passes": 0}
        status["stages"].append(st)
        p = 0
        while p < (1 if a.dry_run else a.max_passes):
            p += 1
            st["passes"] = p
            write(f"START {name} (pass {p}): {' '.join(cmd)}")
            started = now()
            r = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
            log.write(r.stdout[-20000:] + r.stderr[-5000:] + "\n"); log.flush()
            # full, untruncated stage output: one file per stage pass
            stage_dir = LOGS / "stages" / (a.queue + ("-dry" if a.dry_run else ""))
            stage_dir.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            (stage_dir / f"{started.replace(':', '')}__{slug}__pass{p}.log").write_text(
                f"# {' '.join(cmd)}\n# started {started}, ended {now()}, rc={r.returncode}\n"
                f"## stdout\n{r.stdout}\n## stderr\n{r.stderr}\n")
            errs = sum(int(m.group(2)) for m in DONE_RE.finditer(r.stdout))
            oks = sum(int(m.group(1)) for m in DONE_RE.finditer(r.stdout))
            st.update({"last_ok": oks, "last_errors": errs, "returncode": r.returncode})
            status_path.write_text(json.dumps(status, indent=2))
            summary = [l for l in r.stdout.splitlines() if "jobs," in l or l.startswith("  ") and "calls" in l]
            write(f"END   {name} (pass {p}): rc={r.returncode} ok={oks} errors={errs} | " + " ; ".join(summary)[:600])
            lim = LIMIT_RE.search(r.stdout)
            if lim and not a.dry_run:
                wait = seconds_until_reset(lim.group(1))
                st["waiting_for_reset"] = lim.group(1)[:200]
                status_path.write_text(json.dumps(status, indent=2))
                write(f"USAGE LIMIT in {name}: {lim.group(1)[:200]} -> sleeping {wait // 60} min, then resuming this stage")
                wall_sleep(wait)
                st.pop("waiting_for_reset", None)
                p -= 1  # a usage window is not a failed pass
                continue
            if r.returncode != 0 and errs == 0:
                # a crash, not job errors: retry the stage (resuming) after a pause, rather
                # than moving on and silently leaving it unfinished (2026-11-05: drift core)
                if p < a.max_passes and not a.dry_run:
                    write(f"STAGE CRASHED {name} (pass {p}): {r.stderr.strip()[-400:]}")
                    write(f"pausing {a.pause_min} min before retrying {name}")
                    wall_sleep(a.pause_min * 60)
                    continue
                write(f"STAGE FAILED {name} after {p} passes: {r.stderr.strip()[-400:]}")
                break
            if errs == 0 or a.dry_run:
                break
            write(f"{errs} errors in {name}; pausing {a.pause_min} min before retrying")
            wall_sleep(a.pause_min * 60)
        st["finished"] = now()
        status_path.write_text(json.dumps(status, indent=2))
    status["finished"] = now()
    status_path.write_text(json.dumps(status, indent=2))
    write(f"QUEUE {a.queue} FINISHED")


if __name__ == "__main__":
    main()
