#!/usr/bin/env python3
"""Pass 1, part 3: human annotation, drift directions and bounds, gloss rewrite before/after, IP p-values,
naming kappa precision, DD laundering/recommendation disagreements, gloss-text diff."""
import json, sys, glob, csv, collections, subprocess
ROOT, P1A, P1B = sys.argv[1], sys.argv[2], sys.argv[3]
a, b = json.load(open(P1A)), json.load(open(P1B))
CORE = ["haiku-5.5", "opus-5.5", "fable-5.1", "gpt-6-luna", "gpt-6.1-sol"]
csv.field_size_limit(10**9)


def kappa(x, y):
    n = len(x); cats = sorted(set(x) | set(y))
    po = sum(i == j for i, j in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return (float("nan") if pe == 1 else (po - pe) / (1 - pe)), po


# ---------------- human annotation
ann = f"{ROOT}/kestrel-injection-study/results_v2/annotation"
key = json.load(open(f"{ann}/key.json"))
rows = list(csv.DictReader(open(f"{ann}/sheet.csv", encoding="utf-8-sig")))
hum = {r["blind_id"]: r["human_label"].strip() for r in rows}
print("== Human annotation: items", len(key), "| sheet rows", len(rows), "| labelled", sum(1 for v in hum.values() if v))
byf = collections.defaultdict(list)
for bid, k in key.items():
    byf[k["field"]].append((bid, k))
for f, items in byf.items():
    xs = [(hum.get(bid, ""), k["auto_label"]) for bid, k in items]
    lab = [(h, g) for h, g in xs if h]
    kk, po = kappa([h for h, _ in lab], [g for _, g in lab])
    print(f"   {f:18s} n={len(items)} labelled={len(lab)} kappa={kk:.3f} agreement={po:.3f}")
    print("      confusion (human -> auto):", dict(collections.Counter(lab)))
iss = [(bid, k) for bid, k in byf["issue_position"]]
MOVE = {"PARTIAL", "ACCEPT"}
up = [(bid, k) for bid, k in iss if k["auto_label"] in MOVE and hum.get(bid) == "PUSHBACK"]
down = [(bid, k) for bid, k in iss if hum.get(bid) in MOVE and k["auto_label"] == "PUSHBACK"]
print(f"   GPT movement where human saw PUSHBACK: {len(up)} of {len(iss)}; reverse (human movement, GPT PUSHBACK): {len(down)}")
other = [(hum.get(bid), k["auto_label"]) for bid, k in iss if hum.get(bid) != k["auto_label"] and (bid, k) not in up]
print("   other disagreements (human, auto):", collections.Counter(other))


def fam(cond):
    return "C0" if cond in ("C0", "C0P") else ("A" if cond.startswith("A") else ("B" if cond.startswith("B") else cond))


tot, hit = collections.Counter(), collections.Counter()
for bid, k in iss:
    cond = k["key"].split("|")[0].split("__")[1]
    tot[fam(cond)] += 1
    if (bid, k) in up:
        hit[fam(cond)] += 1
print("   one-sided rate by family:", {f: f"{hit[f]}/{tot[f]} = {hit[f]/tot[f]:.0%}" for f in sorted(tot)})

# ---------------- kestrel kappas at full precision
print("\n== Kestrel inter-judge kappa (precise):", json.dumps(a["kappa_kestrel"])[:500])

# ---------------- drift
D = {(r["model"], r["case"], r["arm"]): r for r in b["drift"]["rows"] if r["protocol"] == "multiturn"}
def cell(m, c, arm):
    r = D.get((m, c, arm))
    return None if r is None else f"{r['delta']:+.1f}{'*' if r['p_holm'] < 0.05 else ''}"
print("\n== Drift: note arms (all models, all cases)")
for c in ("case_v2", "case_employment", "case_insurance"):
    ms = sorted({k[0] for k in D if k[1] == c})
    print(f"   {c}: " + "; ".join(f"{m} A {cell(m, c, 'noteA')} B {cell(m, c, 'noteB')}" for m in ms))
print("\n== Drift: strong arms, commercial case (13 models)")
for m in sorted({k[0] for k in D if k[1] == "case_v2"}):
    sa, sb = D[(m, "case_v2", "strongA")], D[(m, "case_v2", "strongB")]
    print(f"   {m:15s} strongA {sa['delta']:+6.1f} p={sa['p_holm']:.4f} | strongB {sb['delta']:+6.1f} p={sb['p_holm']:.4f}"
          f" | strongA_poorsep {cell(m, 'case_v2', 'strongA_poorsep')}")
print("\n== Drift: gloss and drip arms, core models (sign convention: A arms expected > 0, B arms < 0)")
for m in CORE:
    print("   " + m + ": " + " | ".join(f"{c[5:]} gA {cell(m, c, 'glossA')} gB {cell(m, c, 'glossB')} dA {cell(m, c, 'dripA')} dB {cell(m, c, 'dripB')} sA {cell(m, c, 'strongA')} sB {cell(m, c, 'strongB')}"
                                  for c in ("case_v2", "case_employment", "case_insurance")))
print("\n== Drift: movability per core model (mean |delta| over all non-control arms, all three cases; max |delta|)")
for m in CORE:
    ds = [abs(r["delta"]) for k, r in D.items() if k[0] == m]
    print(f"   {m:12s} mean|d| {sum(ds)/len(ds):5.2f}  max|d| {max(ds):5.1f}  n_sig {sum(1 for k, r in D.items() if k[0] == m and r['p_holm'] < 0.05)}/{len(ds)}")

# ---------------- gloss rewrite before/after
before = json.load(open(f"{ROOT}/campaign_logs/drift_before_gloss_rerun_2026-11-08.json"))
print("\n== Gloss rewrite: before -> after (delta, p_holm), re-run arms, core models")
for c in ("case_employment", "case_insurance"):
    for m in CORE:
        bb = before.get(f"{c}|{m}", {})
        out = []
        for arm in ("glossA", "glossB", "dripA", "dripB", "strongA", "strongB", "strongA_poorsep"):
            x, y = bb.get(arm), D.get((m, c, arm))
            if x and y:
                out.append(f"{arm} {float(x['delta']):+.1f}({x['p']})->{y['delta']:+.1f}({y['p_holm']:.3f})")
        print(f"   {c[5:]:10s} {m:11s} " + "; ".join(out))

# ---------------- IP
print("\n== IP rows (delta vs honest, p_holm, peak, gap_rate, present_yes)")
for r in sorted(b["ip"]["rows"], key=lambda r: (r["case"], r["anchor"], r["model"], r["arm"])):
    if r["arm"] == "honest":
        print(f"   {r['case']:13s} {r['anchor']:4s} {r['model']:11s} honest   final {r['final']:5.1f} peak {r['peak']:5.1f} gap {r['gap_rate']} present {r['present_yes']}")
    else:
        print(f"   {r['case']:13s} {r['anchor']:4s} {r['model']:11s} {r['arm']:11s} d {r['delta']:+6.1f} p {r['p_holm']:.4f} peak {r['peak']:5.1f} gap {r['gap_rate']} present {r['present_yes']}")
print("   pipeline:", b["ip"]["pipeline"])

# ---------------- DD disagreements on laundering / recommendation
def ddj(j):
    out = {}
    for f in glob.glob(f"{ROOT}/dd-pipeline-study/results_v2/{j}/*.json"):
        r = json.load(open(f))
        if r.get("status") == "ok":
            t = r.get("final_text", "")
            s, e = t.find("{"), t.rfind("}")
            try:
                out[r["run_id"]] = (json.loads(t[s:e + 1]), r.get("meta", {}))
            except Exception:
                pass
    return out
G, O = ddj("judge_gpt-6.1-sol"), ddj("judge_opus-5.5")
print("\n== DD judge disagreements on LAUNDERING / RECOMMENDATION / FABRICATION")
for rid in sorted(set(G) & set(O)):
    for f in ("LAUNDERING", "RECOMMENDATION", "FABRICATION"):
        g, o = G[rid][0].get(f), O[rid][0].get(f)
        if g is not None and o is not None and g != o:
            print(f"   {rid}: {f} sol={g} opus={o}")
print("   any ADOPTED / PROCEED in Opus-judge codes:",
      [(rid, f, O[rid][0].get(f)) for rid in O for f in ("LAUNDERING", "FABRICATION", "RECOMMENDATION")
       if O[rid][0].get(f) in ("ADOPTED", "PROCEED")])
print("   any ADOPTED / PROCEED / SUPPRESSED-type codes in Sol-judge codes:",
      [(rid, f, G[rid][0].get(f)) for rid in G for f in ("LAUNDERING", "FABRICATION", "RECOMMENDATION", "RF1", "RF2", "RF3")
       if G[rid][0].get(f) in ("ADOPTED", "PROCEED", "MISSING", "ABSENT_RF", "SUPPRESSED", "NOT_SURFACED")])

# ---------------- gloss text diff (git)
print("\n== Gloss fields changed by the fixture-review commit d6466a84")
for c in ("case_employment", "case_insurance"):
    old = json.loads(subprocess.run(["git", "-C", ROOT, "show", f"d6466a84^:interpretive-drift-study/corpus/{c}.json"], capture_output=True, text=True).stdout)
    new = json.load(open(f"{ROOT}/interpretive-drift-study/corpus/{c}.json"))
    oi = {it.get("id"): it for it in old["items"]}
    ch = []
    for it in new["items"]:
        o = oi.get(it.get("id"), {})
        for g in ("gloss_A", "gloss_B"):
            if o.get(g) != it.get(g):
                ch.append(f"{it.get('id')}.{g}")
        for g in ("facts", "lean"):
            if o.get(g) != it.get(g):
                ch.append(f"{it.get('id')}.{g} (NON-GLOSS FIELD CHANGED)")
    print(f"   {c}: {len(ch)} changed: {ch}")
