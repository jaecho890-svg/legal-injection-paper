#!/usr/bin/env python3
"""Compare Pass 1's independent recomputation with the original analysis outputs."""
import json, re, sys, collections, glob, math
ROOT, P1A, P1B = sys.argv[1], sys.argv[2], sys.argv[3]
a, b = json.load(open(P1A)), json.load(open(P1B))
issues_found = []

# ---- Kestrel: cells.json vs recomputed
orig = {(c["model"], c["task"], c["guard"], c["condition"]): c for c in json.load(open(f"{ROOT}/kestrel-injection-study/results_v2/analysis/cells.json"))}
mine = {(c["model"], c["task"], c["guard"], c["condition"]): c for c in a["kestrel"]["cells"]}
n_cmp = flips = border = 0
for k, m in mine.items():
    o = orig.get(k)
    if o is None:
        issues_found.append(f"KESTREL cell missing in original: {k}"); continue
    n_cmp += 1
    if o["n"] != m["n"] or abs(o["mean_skew"] - m["mean"]) > 1e-9:
        issues_found.append(f"KESTREL n/mean differ {k}: orig n={o['n']} mean={o['mean_skew']:.3f} vs mine n={m['n']} mean={m['mean']:.3f}")
    if "delta" in m and o.get("delta") is not None:
        if abs(o["delta"] - m["delta"]) > 1e-9:
            issues_found.append(f"KESTREL delta differs {k}: {o['delta']:.3f} vs {m['delta']:.3f}")
        so, sm = (o["p_holm"] or 1) < 0.05, m["p_holm"] < 0.05
        if so != sm:
            flips += 1; issues_found.append(f"KESTREL significance flips under seed 7 {k}: orig p_holm={o['p_holm']:.4f} vs mine {m['p_holm']:.4f}")
        elif 0.02 < min(o["p_holm"] or 1, m["p_holm"]) < 0.08:
            border += 1; print(f"  borderline (both agree) {k}: orig {o['p_holm']:.4f} / mine {m['p_holm']:.4f}")
print(f"Kestrel: {n_cmp} cells compared, {flips} significance flips")

# ---- parse markdown summary tables (drift, IP)
def md_rows(path, header_re):
    out = {}; sec = None
    for line in open(path):
        h = re.match(header_re, line)
        if h: sec = h.groups(); continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if sec and len(c) >= 5 and re.fullmatch(r"[A-Za-z_]+", c[0]) and c[0] != "arm":
            out[sec + (c[0],)] = c
    return out

def num(s):
    s = s.split()[0]
    return 0.0005 if s.startswith("<") else float(s)

dr = md_rows(f"{ROOT}/interpretive-drift-study/results_v2/analysis/summary.md", r"## (\S+) · (\S+) · (\S+)")
n_cmp = flips = 0
for r in b["drift"]["rows"]:
    k = (r["model"], r["case"], r["protocol"], r["arm"]); o = dr.get(k)
    if o is None:
        issues_found.append(f"DRIFT row missing in summary: {k}"); continue
    n_cmp += 1
    if int(o[1]) != r["n"] or abs(num(o[2]) - r["final"]) > 0.051 or abs(num(o[3]) - r["delta"]) > 0.051:
        issues_found.append(f"DRIFT n/final/delta differ {k}: summary n={o[1]} final={o[2]} d={o[3]} vs mine n={r['n']} final={r['final']:.2f} d={r['delta']:.2f}")
    so, sm = num(o[4]) < 0.05, r["p_holm"] < 0.05
    if so != sm:
        flips += 1; issues_found.append(f"DRIFT significance flips under seed 7 {k}: summary p={o[4]} vs mine {r['p_holm']:.4f}")
print(f"Drift: {n_cmp} rows compared, {flips} significance flips")

ip = md_rows(f"{ROOT}/ip-assignment-study/results_v2/analysis/summary.md", r"## (\S+) · (\S+) · \S+ · (\S+) anchor")
n_cmp = flips = 0
for r in b["ip"]["rows"]:
    k = (r["model"], r["case"], r["anchor"], r["arm"]); o = ip.get(k)
    if o is None:
        issues_found.append(f"IP row missing in summary: {k}"); continue
    n_cmp += 1
    if int(o[1]) != r["n"] or abs(num(o[2]) - r["final"]) > 0.051:
        issues_found.append(f"IP n/final differ {k}: summary n={o[1]} final={o[2]} vs mine n={r['n']} final={r['final']:.2f}")
    if r["delta"] is not None:
        if abs(num(o[3]) - r["delta"]) > 0.051:
            issues_found.append(f"IP delta differs {k}: {o[3]} vs {r['delta']:.2f}")
        so, sm = num(o[4]) < 0.05, (r["p_holm"] if r["p_holm"] is not None else 1) < 0.05
        if so != sm:
            flips += 1; issues_found.append(f"IP significance flips under seed 7 {k}: summary p={o[4]} vs mine {r['p_holm']:.4f}")
    if abs(num(o[5]) - r["peak"]) > 0.051:
        issues_found.append(f"IP peak differs {k}: summary {o[5]} vs mine {r['peak']:.2f}")
print(f"IP: {n_cmp} rows compared, {flips} significance flips")

print("\n=== differences found:" if issues_found else "\n=== no differences between Pass 1 and the original analysis outputs")
for x in issues_found:
    print(" -", x)
