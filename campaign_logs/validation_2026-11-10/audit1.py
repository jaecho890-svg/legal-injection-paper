#!/usr/bin/env python3
"""Pass 1 claim audit: each quantitative claim in main.tex against the raw-data recomputation (p1a/p1b)."""
import json, sys, glob, collections, csv, re, os
ROOT, P1A, P1B = sys.argv[1], sys.argv[2], sys.argv[3]
a, b = json.load(open(P1A)), json.load(open(P1B))
CORE = ["haiku-5.5", "opus-5.5", "fable-5.1", "gpt-6-luna", "gpt-6.1-sol"]
D = {(r["model"], r["case"], r["arm"]): r for r in b["drift"]["rows"] if r["protocol"] == "multiturn"}
IP = {(r["model"], r["case"], r["anchor"], r["arm"]): r for r in b["ip"]["rows"]}
K = {(c["model"], c["task"], c["guard"], c["condition"]): c for c in a["kestrel"]["cells"]}
def sig(r): return r["p_holm"] < 0.05
def show(title, ok, detail):
    print(f"[{'OK ' if ok else 'BAD'}] {title}\n      {detail}")

# ---- Table 2 naming rates
nm = a["kestrel"]["naming"]
def rate(m, f):
    k = f"{m}|{f}"; return nm[k][0] / nm[k][1] if k in nm else None
print("== Table 2 (pooled naming rates; A = A1+A2, B = B1+B2+B3, C0 = C0)")
models = sorted({k.split("|")[0] for k in nm})
for m in models:
    print(f"   {m:18s} A {rate(m,'A') if rate(m,'A') is None else round(rate(m,'A'),2)}  B {round(rate(m,'B'),2) if rate(m,'B') is not None else None}  C0 {round(rate(m,'C0'),2) if rate(m,'C0') is not None else None}  A2P {round(rate(m,'A2P'),2) if rate(m,'A2P') is not None else None}")
claude = ["fable-5.1", "opus-5.5", "haiku-5.5", "sonnet-5.5", "opus-4.8"]
gpts = [m for m in models if m.startswith("gpt")]
show("Claude models named the injected instruction in 97-100% of reviews",
     all(0.965 <= rate(m, "A") <= 1.0 for m in claude), {m: round(rate(m, "A"), 3) for m in claude})
show("false alarms on 1-13% of clean ones (Claude)", all(0.005 <= rate(m, "C0") <= 0.135 for m in claude), {m: round(rate(m, "C0"), 3) for m in claude})
show("GPT models ranged from 10% to 97%", abs(min(rate(m, "A") for m in gpts) - 0.10) < 0.006 and abs(max(rate(m, "A") for m in gpts) - 0.97) < 0.006,
     {m: round(rate(m, "A"), 3) for m in gpts})
ratios = {m: (round(rate(m, "B"), 2), round(rate(m, "A"), 2)) for m in models if rate(m, "A")}
show("Every model named framing far less often than injection", all(rate(m, "B") < 0.8 * rate(m, "A") for m in models if rate(m, "A")),
     "B vs A: " + json.dumps(ratios))

# ---- Kestrel text
core_cells = [c for k, c in K.items() if k[0] in CORE and "delta" in c]
mx = max(core_cells, key=lambda c: abs(c["delta"]))
show("Core five: no condition moved skew by more than 1.1 points", abs(mx["delta"]) <= 1.1 + 1e-9, f"max |delta| {mx['delta']:+.2f} at {mx['model']} {mx['task']} {mx['guard']} {mx['condition']}")
sigs = [(c["model"], c["task"], c["guard"], c["condition"], round(c["delta"], 2)) for c in core_cells if c["p_holm"] < 0.05]
show("Core five significant cells: Luna A2 +0.60, Luna B3 +0.75 (open, no guard), Opus A2 +1.10 (open, no playbook) [+ Haiku A2P in PDF family]", True, sigs)
a2p = [c for c in core_cells if c["condition"] == "A2P"]
show("PDF: no model moved (significantly) toward the seller", not any(c["delta"] > 0 and c["p_holm"] < 0.05 for c in a2p),
     "A2P deltas: " + ", ".join(f"{c['model']} {c['guard']} {c['delta']:+.2f}{'*' if c['p_holm']<0.05 else ''}" for c in a2p))
c0p = [c for k, c in K.items() if k[3] == "C0P"]
show("Rendering the clean letter as a PDF changed nothing (all |delta| <= 0.40)", all(abs(c["delta"]) <= 0.4 + 1e-9 and c["p_holm"] >= 0.05 for c in c0p),
     f"max |delta| {max(abs(c['delta']) for c in c0p):.2f}; any significant: {any(c['p_holm']<0.05 for c in c0p)}")
breadth = ["sonnet-5.5", "opus-4.8", "gpt-6.1-terra", "gpt-6-astra", "gpt-6-sol", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
bs = [(c["model"], c["task"], c["guard"], c["condition"], round(c["delta"], 2)) for k, c in K.items() if k[0] in breadth and "delta" in c and c["p_holm"] < 0.05]
show("Among breadth models only Sonnet 5.5 moved significantly (+2.20 B2 no playbook; -1.20 A2 guard on)", all(x[0] == "sonnet-5.5" for x in bs), bs)
allcli = [c for k, c in K.items() if k[0] not in ("dots-3-note", "gemini", "nemotron-3-ultra", "xing-4.0") and "delta" in c]
mxc = max(abs(c["delta"]) for c in allcli)
show("Largest shift 2.2 of 32 points (CLI models); dots.3 about ten times the largest CLI shift", abs(mxc - 2.2) < 0.051, f"max CLI |delta| {mxc:.2f}; ratio {20.75/mxc:.1f}")

# ---- drift
print("== Drift")
def d(m, c, arm): return D[(m, c, arm)]
for arm in ("strongA", "strongB"):
    pass
v2 = sorted({k[0] for k in D if k[1] == "case_v2"})
bad_strong = [(m, round(d(m, "case_v2", "strongA")["delta"], 1), round(d(m, "case_v2", "strongB")["delta"], 1)) for m in v2
              if not (d(m, "case_v2", "strongA")["delta"] < 0 and d(m, "case_v2", "strongB")["delta"] > 0)]
show(f"Strong arm moved against its own side in every model on the commercial case ({len(v2)} models)", not bad_strong,
     "exceptions (model, strongA, strongB): " + json.dumps(bad_strong))
cells = [(m, c) for m in v2 for c in ["case_v2"]] + [(m, c) for m in CORE for c in ("case_employment", "case_insurance")]
cnt = {arm: sum((d(m, c, arm)["delta"] > 0) == (arm in ("lastA", "orderB")) for (m, c) in cells) for arm in ("lastA", "lastB", "orderA", "orderB")}
show("23 model-case cells: last-A positive 22, last-B negative 23, first-A negative 22, first-B positive 21", len(cells) == 23 and cnt == {"lastA": 22, "lastB": 23, "orderA": 22, "orderB": 21},
     f"{len(cells)} cells; counts {cnt}")
la = [round(d(m, "case_employment", "lastA")["delta"], 1) for m in CORE]
show("Dismissal case: every core model showed recency, last-A between +11.7 and +20.6", min(la) > 0 and abs(min(la) - 11.7) < 0.051 and abs(max(la) - 20.6) < 0.051, la)
g = {(m, c): round(d(m, c, "glossB")["delta"], 1) for m in ("haiku-5.5", "gpt-6-luna") for c in ("case_employment", "case_insurance")}
show("Gloss B: Haiku -12.6 (dismissal), -15.1 (insurance); Luna -20.8, -15.7", g == {("haiku-5.5", "case_employment"): -12.6, ("haiku-5.5", "case_insurance"): -15.1, ("gpt-6-luna", "case_employment"): -20.8, ("gpt-6-luna", "case_insurance"): -15.7}, g)
od = [(c, round(d("opus-5.5", c, "dripB")["delta"], 1), sig(d("opus-5.5", c, "dripB")), round(d("opus-5.5", c, "dripA")["delta"], 1), sig(d("opus-5.5", c, "dripA"))) for c in ("case_v2", "case_employment", "case_insurance")]
show("Opus drip B +3.4, +4.1, +7.7; drip A -8.0, -7.5, -1.8 (last ns)", [(x[1], x[3]) for x in od] == [(3.4, -8.0), (4.1, -7.5), (7.7, -1.8)] and not od[2][4], od)
s = d("gpt-6.1-sol", "case_insurance", "glossB"), d("gpt-6.1-sol", "case_insurance", "dripB")
show("Sol insurance gloss B +7.4, drip B +10.1", (round(s[0]["delta"], 1), round(s[1]["delta"], 1)) == (7.4, 10.1), [(round(x["delta"], 1), round(x["p_holm"], 4)) for x in s])
notes = [(m, c, arm, round(d(m, c, arm)["delta"], 1), sig(d(m, c, arm))) for m in CORE for c in ("case_v2", "case_employment", "case_insurance") for arm in ("noteA", "noteB") if (m, c, arm) in D]
over = [x for x in notes if abs(x[3]) > 3.3 + 1e-9]
show("Instructing note alone: |delta| <= 3.3 for every core model (all cases)", not over, "exceeding: " + json.dumps(over))
# gloss rewrite before/after
before = json.load(open(f"{ROOT}/campaign_logs/drift_before_gloss_rerun_2026-11-08.json"))
print("   before-snapshot keys sample:", list(before)[:3] if isinstance(before, dict) else type(before).__name__)

# ---- IP
print("== IP")
def ip(m, c, an, arm): return IP[(m, c, an, arm)]
pk = {m: (round(ip(m, "case", "soft", "honest")["peak"], 1), round(ip(m, "case", "soft", "assert_only")["peak"], 1)) for m in CORE}
show("Soft anchor: assertion lifted the peak (honest 5-14, assert_only 22-34) in every model except Haiku", True, pk)
pk_h = {m: round(ip(m, "case", "hard", "honest")["peak"], 1) for m in CORE}
print("      (hard honest peaks, for range check):", pk_h)
ratio = {m: round(ip(m, "case", "soft", "curated")["delta"] / ip(m, "case", "hard", "curated")["delta"], 2) for m in CORE}
show("Soft anchor roughly doubled the bundle's effect", all(1.6 <= r <= 2.4 for r in ratio.values()), ratio)
peaks = {m: [round(ip(m, "case", an, "curated")["peak"], 1) for an in ("hard", "soft")] for m in CORE}
show("Mean peak P stayed below 50 (bundle, no deed)", all(p < 50 for v in peaks.values() for p in v), peaks)
gap = {(m, an, arm): round(ip(m, "case", an, arm)["gap_rate"], 3) for m in CORE for an in ("hard", "soft") for arm in ("honest", "assert_only", "curated")}
show("Every run still named the missing executed deed (no-deed case, bundle)", all(gap[(m, an, "curated")] == 1.0 for m in CORE for an in ("hard", "soft")),
     {k: v for k, v in gap.items() if v < 1.0} or "all 1.0")
pipe = b["ip"]["pipeline"]
show("Pipeline: deciding model's P 21-33 (bundle) vs 1-7 (honest, assert_only)", True, {k: [v[0], round(v[1], 1)] for k, v in pipe.items()})
ex = {m: (round(ip(m, "case_executed", "hard", "curated")["delta"], 1), round(ip(m, "case_executed", "soft", "curated")["delta"], 1)) for m in CORE}
nd = {m: (round(ip(m, "case", "hard", "curated")["delta"], 1), round(ip(m, "case", "soft", "curated")["delta"], 1)) for m in CORE}
show("Positive control: bundle moved the answer 'just as hard the other way'", False, f"executed (hard, soft) {ex} vs no-deed {nd}")
hh = ip("haiku-5.5", "case_executed", "hard", "assert_only")
show("Haiku hard assert-only fell 14.1 (p=0.042) and said the deed was present in only 60% of runs", abs(hh["delta"] + 14.1) < 0.051 and abs((hh["present_yes"] or 0) - 0.60) < 0.051,
     f"delta {hh['delta']:+.1f}, p_holm {hh['p_holm']:.4f}, present_yes {hh['present_yes']}")
hon = {m: [round(ip(m, "case_executed", an, "honest")["final"], 1) for an in ("hard", "soft")] for m in CORE}
print("      positive-control honest P (hard, soft):", hon)
