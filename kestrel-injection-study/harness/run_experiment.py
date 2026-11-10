#!/usr/bin/env python3
"""
run_experiment.py - backend-agnostic runner.

Usage:
  python run_experiment.py --plan pilot --backend manual   # write prompt files for any reviewer
  python run_experiment.py --plan pilot --backend api --model claude-opus-4-8
  python run_experiment.py --plan full   --backend manual

Backends:
  manual  -> writes results/prompts/<run_id>.json (system+user). Feed to ANY model
             (a Claude Code sub-agent, the opposing-counsel tool, etc.) and drop the
             reviewer's reply into results/runs/<run_id>.response.txt. Then run score.py.
  api     -> calls the Anthropic Messages API (needs ANTHROPIC_API_KEY) and writes the
             response straight to results/runs/<run_id>.response.txt.
"""
import argparse, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reviewer_prompt as rp

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
VARIANTS = ROOT / "corpus" / "variants"

# A plan is a list of (condition, task_structure, guard, replicate)
PLANS = {
    # Pilot: realistic default cell (OPEN/GUARD_ON) across control + injection + framing,
    # clean replicated x2 for a noise floor, plus one CHECKLIST run to show the task defense.
    "pilot": [
        ("C0", "OPEN", "GUARD_ON", 1),
        ("C0", "OPEN", "GUARD_ON", 2),
        ("A1", "OPEN", "GUARD_ON", 1),
        ("B1", "OPEN", "GUARD_ON", 1),
        ("B3", "OPEN", "GUARD_ON", 1),
        ("B3", "CHECKLIST", "GUARD_ON", 1),
    ],
    # Full grid: 6 conditions x 2 task x 2 guard (x replicates added by --replicates)
    "full": [(c, t, g, 1)
             for c in ["C0", "A1", "A2", "B1", "B2", "B3"]
             for t in ["OPEN", "CHECKLIST"]
             for g in ["GUARD_ON", "GUARD_OFF"]],
}

def run_id(cond, task, guard, rep):
    return f"{cond}__{task}__{guard}__r{rep}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="pilot", choices=PLANS.keys())
    ap.add_argument("--backend", default="manual", choices=["manual", "api"])
    ap.add_argument("--model", default="claude-opus-4-8")
    args = ap.parse_args()

    (RESULTS / "prompts").mkdir(parents=True, exist_ok=True)
    (RESULTS / "runs").mkdir(parents=True, exist_ok=True)

    plan = PLANS[args.plan]
    index = []
    for cond, task, guard, rep in plan:
        rid = run_id(cond, task, guard, rep)
        text = (VARIANTS / f"{cond}.txt").read_text()
        p = rp.build(text, task, guard)
        (RESULTS / "prompts" / f"{rid}.json").write_text(
            json.dumps({"run_id": rid, "condition": cond, "task": task, "guard": guard,
                        "replicate": rep, **p}, indent=2))
        index.append({"run_id": rid, "condition": cond, "task": task, "guard": guard, "replicate": rep})
    (RESULTS / "run_index.json").write_text(json.dumps(index, indent=2))
    print(f"[plan={args.plan}] wrote {len(index)} prompt files to results/prompts/")

    if args.backend == "api":
        _run_api(index, args.model)
    else:
        print("Backend=manual: feed each results/prompts/<run_id>.json to a reviewer model,")
        print("save the reply to results/runs/<run_id>.response.txt, then run score.py.")

def _run_api(index, model):
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic, and set ANTHROPIC_API_KEY")
    client = anthropic.Anthropic()
    for row in index:
        p = json.loads((RESULTS / "prompts" / f"{row['run_id']}.json").read_text())
        msg = client.messages.create(model=model, max_tokens=4000, system=p["system"],
                                      messages=[{"role": "user", "content": p["user"]}])
        out = "".join(b.text for b in msg.content if b.type == "text")
        (RESULTS / "runs" / f"{row['run_id']}.response.txt").write_text(out)
        print("ran", row["run_id"], f"({len(out)}c)")

if __name__ == "__main__":
    main()
