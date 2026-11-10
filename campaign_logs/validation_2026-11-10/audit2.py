#!/usr/bin/env python3
"""Pass 1, part 2: DD claims, DD inter-judge kappa (all co-coded items), human-annotation statistics."""
import json, sys, glob, collections, csv, os, re
ROOT, P1B = sys.argv[1], sys.argv[2]
b = json.load(open(P1B))
exec(open("pass1.py").read().split("# ------------------------------------------------------------------ Kestrel")[0]
     .replace("ROOT, OUT = sys.argv[1], sys.argv[2]", "ROOT, OUT = sys.argv[1], '/dev/null'")
     .replace("SECTIONS = sys.argv[3:] or", "SECTIONS = [] or")
     .replace("if os.path.exists(OUT):\n    res = json.load(open(OUT))", ""))

G = b["dd"]["groups"]
print("== DD groups (target|corpus|level|parser|orchestrator : n, key fields)")
for k, v in G.items():
    f = v["fields"]
    keep = {fld: f[fld] for fld in ("HEDGE", "LONE_FLAG", "ADMISSION", "CLUSTER", "FABRICATION", "LAUNDERING", "RECOMMENDATION", "RF1", "RF2", "RF3") if fld in f}
    print(f"  {k:60s} n={v['n']:3d} {json.dumps(keep)}")

# DD inter-judge over every item coded by both judges
def ddj(j):
    out = {}
    for f in glob.glob(f"{ROOT}/dd-pipeline-study/results_v2/{j}/*.json"):
        r = json.load(open(f))
        if r.get("status") == "ok":
            o = extract(r.get("final_text", ""))
            if isinstance(o, dict):
                out[r["run_id"]] = o
    return out
DG, DO = ddj("judge_gpt-6.1-sol"), ddj("judge_opus-5.5")
both = sorted(set(DG) & set(DO))
print(f"\n== DD inter-judge: items coded by both = {len(both)}")
for fld in sorted({k for r in both for k, v in DO[r].items() if isinstance(v, (str, bool))}):
    pairs = [(str(DG[r][fld]), str(DO[r][fld])) for r in both if fld in DG[r] and fld in DO[r]]
    if pairs:
        kk, po = kappa([x for x, _ in pairs], [y for _, y in pairs])
        print(f"   {fld:26s} n={len(pairs):3d} agreement={po:.2f} kappa={kk if kk == kk else float('nan'):.2f}")

# Human annotation
ann = f"{ROOT}/kestrel-injection-study/results_v2/annotation"
print("\n== annotation files:", os.listdir(ann))
