#!/usr/bin/env python3
"""Recompute every Holm family that contains a near-threshold result (0.01-0.10 in either pass)
with 200,000 permutations, so the significance call does not depend on Monte Carlo noise."""
import json, sys, re, glob, collections, math
import random
from multiprocessing import Pool
ROOT, P1A, P1B = sys.argv[1], sys.argv[2], sys.argv[3]
NPERM = 100_000
a, b = json.load(open(P1A)), json.load(open(P1B))
sys.path.insert(0, ".")
exec(open("pass1.py").read().split("# ------------------------------------------------------------------ Kestrel")[0]
     .replace("ROOT, OUT = sys.argv[1], sys.argv[2]", "ROOT, OUT = sys.argv[1], '/dev/null'")
     .replace("SECTIONS = sys.argv[3:] or", "SECTIONS = [] or")
     .replace("if os.path.exists(OUT):\n    res = json.load(open(OUT))", ""))   # reuse extract/step_ok only


def _perm_job(args):
    x, y, seed = args
    pooled = list(x) + list(y); nx, ny = len(x), len(y); T = sum(pooled)
    obs = abs(sum(x) / nx - sum(y) / ny); rng = random.Random(seed); hits = 0
    for _ in range(NPERM):
        rng.shuffle(pooled); s1 = sum(pooled[:nx])
        if abs(s1 / nx - (T - s1) / ny) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (NPERM + 1)


POOL = None
def perm_many(pairs):
    return POOL.map(_perm_job, [(x, y, 1000 + i) for i, (x, y) in enumerate(pairs)])


def holm(d):
    items = sorted((p, k) for k, p in d.items()); m = len(items); out = {}; run = 0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p)); out[k] = run
    return out

# ---- data (raw) for the families
POS = {"PUSHBACK": 0, "PARTIAL": 1, "ACCEPT": 2, "NOT_ADDRESSED": 2}
iss = json.load(open(f"{ROOT}/kestrel-injection-study/corpus/issues.json"))["issues"]; IDS = [i["id"] for i in iss]
kcells = collections.defaultdict(list)
for f in glob.glob(f"{ROOT}/kestrel-injection-study/results_v2/judge_gpt-6.1-sol/*.json"):
    r = json.load(open(f))
    if r.get("status") != "ok": continue
    o = extract(r["final_text"])
    if not isinstance(o, dict) or not isinstance(o.get("issues"), list): continue
    got = {i.get("issue_id"): i.get("position") for i in o["issues"] if isinstance(i, dict)}
    if not all(got.get(i) in POS for i in IDS): continue
    rid = r["run_id"]; mdl, cond, task, guard, rep = rid.split("__")
    kcells[(mdl, task, guard, cond)].append(sum(POS[got[i]] for i in IDS))

border = []
if __name__ == '__main__':
    import multiprocessing as mp
    mp.set_start_method('fork', force=True)
    POOL = Pool(8)
orig = {(c["model"], c["task"], c["guard"], c["condition"]): c for c in json.load(open(f"{ROOT}/kestrel-injection-study/results_v2/analysis/cells.json"))}
mine = {(c["model"], c["task"], c["guard"], c["condition"]): c for c in a["kestrel"]["cells"] if "p_holm" in c}
fams = set()
for k, m in mine.items():
    po = orig[k]["p_holm"]
    if 0.01 <= min(po, m["p_holm"]) <= 0.10 or 0.01 <= max(po, m["p_holm"]) <= 0.10:
        fams.add((k[:3], "pdf" if k[3] in ("C0P", "A2P") else "main"))
print("Kestrel families to recompute:", len(fams))
for (g, fam) in sorted(fams):
    conds = [c for c in ("A1", "A2", "B1", "B2", "B3") if g + (c,) in kcells] if fam == "main" else [c for c in ("C0P", "A2P") if g + (c,) in kcells]
    raw = dict(zip(conds, perm_many([(kcells[g + (c,)], kcells[g + (("C0P" if c == "A2P" else "C0"),)]) for c in conds])))
    adj = holm(raw)
    for c in conds:
        po = orig[g + (c,)]["p_holm"]; pm = mine[g + (c,)]["p_holm"]
        if 0.005 <= min(po, pm) <= 0.12:
            print(f"  KESTREL {g} {c}: orig {po:.4f} | seed7 {pm:.4f} | 200k {adj[c]:.4f} -> {'SIG' if adj[c] < 0.05 else 'ns'}")

# ---- drift
druns = collections.defaultdict(list)
for f in glob.glob(f"{ROOT}/interpretive-drift-study/results_v2/reviewer/*.json"):
    r = json.load(open(f))
    if r.get("status") != "ok": continue
    m = r["meta"]; n = m["n_items"]; ex = r.get("exchanges", []); ok = True
    for k in range(n):
        if not step_ok(extract(ex[k].get("text", "")) if k < len(ex) else None): ok = False; break
    if not ok or len(ex) <= n: continue
    fin = extract(ex[n].get("text", ""))
    if not step_ok(fin): continue
    druns[(m["model"], m["case"], m["protocol"], m["arm"])].append(int(fin["p"]))
summ = {}
sec = None
for line in open(f"{ROOT}/interpretive-drift-study/results_v2/analysis/summary.md"):
    h = re.match(r"## (\S+) · (\S+) · (\S+)", line)
    if h: sec = h.groups(); continue
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if sec and len(c) >= 5 and re.fullmatch(r"[A-Za-z_]+", c[0]) and c[0] != "arm":
        summ[sec + (c[0],)] = 0.0005 if c[4].startswith("<") else float(c[4])
dfams = set()
for r in b["drift"]["rows"]:
    k = (r["model"], r["case"], r["protocol"], r["arm"]); po = summ[k]
    if 0.01 <= min(po, r["p_holm"]) <= 0.10 or 0.01 <= max(po, r["p_holm"]) <= 0.10:
        dfams.add(k[:3])
print("Drift families to recompute:", len(dfams))
my_d = {(r["model"], r["case"], r["protocol"], r["arm"]): r["p_holm"] for r in b["drift"]["rows"]}
for g in sorted(dfams):
    arms = [k[3] for k in druns if k[:3] == g and k[3] != "control"]
    raw = dict(zip(arms, perm_many([(druns[g + (arm,)], druns[g + ("control",)]) for arm in arms])))
    adj = holm(raw)
    for arm in sorted(arms):
        po, pm = summ[g + (arm,)], my_d[g + (arm,)]
        if 0.005 <= min(po, pm) <= 0.12:
            print(f"  DRIFT {g} {arm}: orig {po:.4f} | seed7 {pm:.4f} | 200k {adj[arm]:.4f} -> {'SIG' if adj[arm] < 0.05 else 'ns'}")

# ---- IP (families of two arms)
for r in b["ip"]["rows"]:
    if r["p_holm"] is not None and 0.005 <= r["p_holm"] <= 0.12:
        print(f"  IP borderline (seed7): {r['model']} {r['case']} {r['anchor']} {r['arm']} p_holm={r['p_holm']:.4f}")
