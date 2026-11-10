#!/usr/bin/env python3
"""make_chart.py - dependency-free SVG line chart of P-trajectories over evidence steps."""
import csv, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"

traj = defaultdict(dict)
with open(RES / "trajectories.csv") as f:
    for r in csv.DictReader(f):
        traj[(r["model"], r["arm"])][int(r["step"])] = int(r["P"])

# which series to plot and how
SERIES = [
    ("opus", "control", "#1d4ed8", "4 4", 0.55, "Opus · control"),
    ("opus", "dripA",   "#1d4ed8", "",    1.0,  "Opus · steer→justified"),
    ("opus", "dripB",   "#1d4ed8", "1 3", 0.8,  "Opus · steer→wrongful"),
    ("haiku","control", "#ea580c", "4 4", 0.55, "Haiku · control"),
    ("haiku","dripA",   "#ea580c", "",    1.0,  "Haiku · steer→justified"),
    ("haiku","dripB",   "#ea580c", "1 3", 0.8,  "Haiku · steer→wrongful"),
]
W, H = 760, 470
L, Rm, T, B = 70, 240, 54, 54           # margins (big right margin for legend)
pw, ph = W - L - Rm, H - T - B
steps = range(1, 9)
def x(s): return L + (s-1)/7*pw
def y(p): return T + (100-p)/100*ph

el = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Roboto,sans-serif">']
el.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
el.append(f'<text x="{L}" y="26" font-size="17" font-weight="700" fill="#0f172a">Running judgment over an 8-item balanced evidence bundle</text>')
el.append(f'<text x="{L}" y="44" font-size="12" fill="#64748b">P(termination was justified). Dashed = no steering · solid = steer up · dotted = steer down. Gap from dashed = steering-induced drift.</text>')
# gridlines + y labels
for p in range(0, 101, 25):
    el.append(f'<line x1="{L}" y1="{y(p):.1f}" x2="{L+pw}" y2="{y(p):.1f}" stroke="#e2e8f0"/>')
    el.append(f'<text x="{L-10}" y="{y(p)+4:.1f}" font-size="11" fill="#94a3b8" text-anchor="end">{p}</text>')
# neutral 50 reference
el.append(f'<line x1="{L}" y1="{y(50):.1f}" x2="{L+pw}" y2="{y(50):.1f}" stroke="#334155" stroke-dasharray="2 4"/>')
el.append(f'<text x="{L+pw-2}" y="{y(50)-6:.1f}" font-size="10.5" fill="#334155" text-anchor="end">50 = genuinely balanced</text>')
# x labels
for s in steps:
    el.append(f'<text x="{x(s):.1f}" y="{T+ph+20:.1f}" font-size="11" fill="#94a3b8" text-anchor="middle">{s}</text>')
el.append(f'<text x="{L+pw/2:.1f}" y="{T+ph+42:.1f}" font-size="12" fill="#475569" text-anchor="middle">evidence item seen (cumulative)</text>')
# series
for model, arm, color, dash, op, _ in SERIES:
    pts = traj.get((model, arm))
    if not pts: continue
    d = " ".join(f"{x(s):.1f},{y(pts[s]):.1f}" for s in steps if s in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2.4" opacity="{op}"{da} stroke-linejoin="round"/>')
    last = max(pts); el.append(f'<circle cx="{x(last):.1f}" cy="{y(pts[last]):.1f}" r="3" fill="{color}" opacity="{op}"/>')
# legend
lx, ly = L+pw+24, T+6
for i,(_,_,color,dash,op,label) in enumerate(SERIES):
    yy = ly + i*26
    da = f' stroke-dasharray="{dash}"' if dash else ""
    el.append(f'<line x1="{lx}" y1="{yy}" x2="{lx+26}" y2="{yy}" stroke="{color}" stroke-width="2.6" opacity="{op}"{da}/>')
    el.append(f'<text x="{lx+32}" y="{yy+4}" font-size="11.5" fill="#334155">{label}</text>')
el.append(f'<text x="{lx}" y="{ly+6*26+10}" font-size="10.5" fill="#64748b">Weaker model (Haiku) drifts</text>')
el.append(f'<text x="{lx}" y="{ly+6*26+24}" font-size="10.5" fill="#64748b">~2× more than Opus under</text>')
el.append(f'<text x="{lx}" y="{ly+6*26+38}" font-size="10.5" fill="#64748b">identical steering.</text>')
el.append("</svg>")
(RES / "trajectories.svg").write_text("\n".join(el))
print("wrote", RES / "trajectories.svg")
