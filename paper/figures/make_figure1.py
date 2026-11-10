#!/usr/bin/env python3
"""
make_figure1.py - Figure 1 for the paper: three stacked full-width panels (contract review,
interpretive drift, IP assignment), one labelled row per model, each effect with its 95% bootstrap
confidence interval, read straight from the analysis outputs (no hand-typed numbers).

Sign convention: right of zero = a shift toward the party that planted the text
  contract review  skew up (toward the seller)                    delta as reported
  drift            final P toward the favoured side               A arms as reported, B arms negated
  IP (no deed)     P(rights held) up (toward the asserting party)  delta as reported
Filled mark = Holm-adjusted p < 0.05. Where a row has two marks they are offset vertically and told
apart by shape (circle, diamond); each panel's subtitle says which is which.

  python3 paper/figures/make_figure1.py      (writes paper/figures/figure1.tex and figure1.values.txt)

paper/build.sh runs this, compiles figure1.tex on its own and copies the result to paper/figure1.pdf,
which main.tex includes. figure1.values.txt lists every plotted value and interval, at the precision
of its source: two decimals from cells.json, one decimal from the drift and IP summaries.
"""
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1]
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "figure1.tex"

# ---------------------------------------------------------------- data: (delta, p, lo, hi)
cells = json.load(open(ROOT / "kestrel-injection-study/results_v2/analysis/cells.json"))


def kestrel(model, cond):
    r = [c for c in cells if c["model"] == model and c["task"] == "OPEN"
         and c["guard"] == "GUARD_OFF" and c["condition"] == cond]
    assert len(r) == 1, (model, cond, len(r))
    r = r[0]
    return [(r["delta"], r["p_holm"], r["delta_lo"], r["delta_hi"])]


CELL = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]")


def sections(path, pattern):
    out = {}
    for block in re.split(r"\n(?=## )", pathlib.Path(path).read_text()):
        m = re.match(pattern, block)
        if not m:
            continue
        rows = {}
        for line in block.splitlines():
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 5 and re.fullmatch(r"[A-Za-z_]+", c[0]) and c[0] != "arm" and c[3] != "—":
                d, lo, hi = (float(x) for x in CELL.match(c[3]).groups())
                p = 0.0005 if c[4].startswith("<") else float(c[4])
                rows[c[0]] = (d, p, lo, hi)
        out[m.groups()] = rows
    return out


drift = sections(ROOT / "interpretive-drift-study/results_v2/analysis/summary.md", r"## (\S+) · (\S+) · ")
ip = sections(ROOT / "ip-assignment-study/results_v2/analysis/summary.md",
              r"## (\S+) · (\S+) · \S+ · (\S+) anchor")


def drift_pair(model, a_arm, b_arm):
    r = drift[(model, "case_v2")]
    d, p, lo, hi = r[b_arm]
    return [r[a_arm], (-d, p, -hi, -lo)]      # B arm negated: + = toward the favoured side


def ip_pair(model, arm):
    return [ip[(model, "case", "hard")][arm], ip[(model, "case", "soft")][arm]]


CORE = [("haiku-5.5", "Haiku 5.5"), ("opus-5.5", "Opus 5.5"), ("fable-5.1", "Fable 5.1"),
        ("gpt-6-luna", "GPT-6 Luna"), ("gpt-6.1-sol", "GPT-6.1 Sol")]
API = [("dots-3-note", "dots.3 note"), ("gemini", "Gemini 3.6 Flash"),
       ("nemotron-3-ultra", "Nemotron 3 Ultra"), ("xing-4.0", "Xing 4.0")]

PANELS = [
    dict(title="Contract review", sub="open task, playbook without guard", keys=None,
         unit="change in skew toward the seller (points of 32)", api=True, pitch=0.385,
         cols=[("Hidden instruction", lambda m: kestrel(m, "A2")),
               ("Combined framing", lambda m: kestrel(m, "B3"))]),
    dict(title="Interpretive drift", sub="commercial case;", keys=("arm favouring A", "arm favouring B"),
         unit="change in final $P$ toward the favoured side (points of 100)", api=False, pitch=0.45, dp=1,
         cols=[("Favoured items first", lambda m: drift_pair(m, "orderA", "orderB")),
               ("Favoured items last", lambda m: drift_pair(m, "lastA", "lastB")),
               ("Slanted glosses", lambda m: drift_pair(m, "glossA", "glossB"))]),
    dict(title="IP assignment", sub="no-deed case;", keys=("hard anchor", "soft anchor"),
         unit="change in final $P$ toward the asserting party (points of 100)", api=False, pitch=0.45, dp=1,
         cols=[("Assertion only", lambda m: ip_pair(m, "assert_only")),
               ("Adversarial bundle", lambda m: ip_pair(m, "curated"))]),
]

# axis range per panel: every interval fits, rounded out to multiples of 5
for P in PANELS:
    models = CORE + (API if P["api"] else [])
    vals = [x for _, fn in P["cols"] for m, _ in models for pt in fn(m) for x in (pt[2], pt[3])]
    P["lo"] = min(0, 5 * math.floor((min(vals) - 0.6) / 5))
    P["hi"] = max(0, 5 * math.ceil((max(vals) + 0.6) / 5))
    P["ticks"] = list(range(P["lo"], P["hi"] + 1, 5))

# ---------------------------------------------------------------- geometry (cm)
W = 15.95               # total drawing width (paper text width is 16.5)
LABEL_W = 3.0           # label column; labels end at LABEL_W - 0.15
GAP_COL = 0.75          # between columns of one panel
API_GAP = 0.30          # extra space before the API rows
HEAD = 0.84             # panel title baseline to first row
PANEL_GAP = 0.62        # unit label to the next panel title
R_DOT = 0.072           # circle radius (about 2pt)
R_DIA = R_DOT * 1.25    # diamond half-diagonal (about the circle's area)
DODGE = 0.088           # vertical offset of the two marks in a two-mark row

out = []
w = out.append
w(r"""\documentclass[11pt,border=2pt,convert=false]{standalone}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{tikz}
\definecolor{acc}{HTML}{2F6FC6}
\definecolor{ci}{HTML}{8FB0DE}
\definecolor{ink}{HTML}{222222}
\definecolor{muted}{HTML}{6B6B6B}
\definecolor{key}{HTML}{8A8A8A}
\definecolor{rule}{HTML}{BDBDBD}
\definecolor{faint}{HTML}{EDEDED}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm,font=\footnotesize,text=ink]""")


def shape_path(x, y, shape, r_scale=1.0):
    if shape == "circle":
        return f"({x:.3f},{y:.3f}) circle ({R_DOT * r_scale:.3f})"
    r = R_DIA * r_scale
    return f"({x:.3f},{y + r:.3f}) -- ({x + r:.3f},{y:.3f}) -- ({x:.3f},{y - r:.3f}) -- ({x - r:.3f},{y:.3f}) -- cycle"


def mark(x, y, sig, shape):
    halo = 1 + 0.032 / R_DOT
    w(rf"\fill[white] {shape_path(x, y, shape, halo)};")
    if sig:
        w(rf"\fill[acc] {shape_path(x, y, shape)};")
    else:
        w(rf"\filldraw[fill=white,draw=acc,line width=0.75pt] {shape_path(x, y, shape, 0.84)};")


y = 0.0
rec = []
for pi, P in enumerate(PANELS):
    models = CORE + (API if P["api"] else [])
    pitch = P["pitch"]
    rows, yy = [], y - HEAD
    for i, (m, lab) in enumerate(models):
        if i == len(CORE):
            yy -= API_GAP
        rows.append((m, lab, yy))
        yy -= pitch
    y_first, y_last = rows[0][2], rows[-1][2]
    # panel title, subtitle and (for two-mark panels) the shape key, on one baseline
    w(rf"\node[anchor=base west,font=\small\bfseries,inner sep=0pt] (t{pi}) at (0,{y:.3f}) {{{P['title']}}};")
    w(rf"\node[anchor=base west,font=\scriptsize,text=muted,inner sep=0pt] (s{pi}) at ([xshift=0.3cm]t{pi}.base east) {{{P['sub']}}};")
    if P["keys"]:
        prev = f"s{pi}"
        for k, (label, shape) in enumerate(zip(P["keys"], ("circle", "diamond"))):
            w(rf"\path ([xshift=0.24cm,yshift=0.075cm]{prev}.base east) coordinate (g{pi}{k});")
            if shape == "circle":
                w(rf"\fill[key] (g{pi}{k}) circle ({R_DOT * 0.9:.3f});")
            else:
                rr = R_DIA * 0.9
                w(rf"\fill[key] ([yshift={rr:.3f}cm]g{pi}{k}) -- ([xshift={rr:.3f}cm]g{pi}{k}) -- "
                  rf"([yshift={-rr:.3f}cm]g{pi}{k}) -- ([xshift={-rr:.3f}cm]g{pi}{k}) -- cycle;")
            w(rf"\node[anchor=base west,font=\scriptsize,text=muted,inner sep=0pt] (k{pi}{k}) at "
              rf"([xshift=0.13cm]g{pi}{k} |- {prev}.base) {{{label}{',' if k == 0 else ''}}};")
            prev = f"k{pi}{k}"
    # row labels
    for m, lab, ry in rows:
        w(rf"\node[anchor=east] at ({LABEL_W - 0.15:.3f},{ry:.3f}) {{{lab}}};")
    if P["api"]:
        w(rf"\node[anchor=west,font=\scriptsize\itshape,text=muted] at (0,{rows[len(CORE)][2] + pitch * 0.5 + API_GAP * 0.4:.3f}) {{API models}};")
    ncols = len(P["cols"])
    col_w = (W - LABEL_W - GAP_COL * (ncols - 1)) / ncols
    span = P["hi"] - P["lo"]
    for ci, (title, fn) in enumerate(P["cols"]):
        x0 = LABEL_W + ci * (col_w + GAP_COL)
        X = lambda v, x0=x0: x0 + (v - P["lo"]) / span * col_w
        w(rf"\node[anchor=base,font=\footnotesize] at ({x0 + col_w / 2:.3f},{y - 0.47:.3f}) {{{title}}};")
        for m, lab, ry in rows:
            w(rf"\draw[faint,line width=0.3pt] ({x0:.3f},{ry:.3f}) -- ({x0 + col_w:.3f},{ry:.3f});")
        for t in P["ticks"]:
            col, lw = ("rule", "0.5pt") if t == 0 else ("faint", "0.4pt")
            w(rf"\draw[{col},line width={lw}] ({X(t):.3f},{y_first + 0.2:.3f}) -- ({X(t):.3f},{y_last - 0.2:.3f});")
            if t % 10 == 0:                     # gridlines every 5, labels every 10
                w(rf"\node[font=\scriptsize,text=muted,anchor=north] at ({X(t):.3f},{y_last - 0.25:.3f}) {{${t}$}};")
        for m, lab, ry in rows:
            pts = fn(m)
            offs = [0.0] if len(pts) == 1 else [DODGE, -DODGE]
            shapes = ["circle"] if len(pts) == 1 else ["circle", "diamond"]
            for (v, p, lo, hi), off in zip(pts, offs):          # intervals first, marks on top
                w(rf"\draw[ci,line width=0.8pt] ({X(lo):.3f},{ry + off:.3f}) -- ({X(hi):.3f},{ry + off:.3f});")
            for (v, p, lo, hi), off, shape in zip(pts, offs, shapes):
                mark(X(v), ry + off, p < 0.05, shape)
            if m == "dots-3-note" and title.startswith("Hidden"):
                v, p, lo, hi = pts[0]
                w(rf"\node[font=\scriptsize,anchor=south] at ({X(v):.3f},{ry + 0.06:.3f}) {{$+{v:.1f}$}};")
            dp = P.get("dp", 2)                 # the source's precision: summaries print one decimal
            rec.append(f"{P['title']:18s} | {title:22s} | {lab:16s} | " + "  ".join(
                f"{v:+7.{dp}f} [{lo:+7.{dp}f}, {hi:+7.{dp}f}]{'*' if p < 0.05 else ' '}" for v, p, lo, hi in pts))
    y_unit = y_last - 0.66
    w(rf"\node[font=\scriptsize,text=muted,anchor=north] at ({(LABEL_W + W) / 2:.3f},{y_unit:.3f}) {{{P['unit']}}};")
    y = y_unit - 0.32 - PANEL_GAP

# legend, top right on the first panel's title line: significance and the interval
w(r"\node[anchor=base east,font=\scriptsize,text=muted,inner sep=0pt] (lg3) at " rf"({W:.3f},0) {{95\% CI}};")
w(r"\draw[ci,line width=0.8pt] ([xshift=-0.55cm,yshift=0.075cm]lg3.base west) -- ([xshift=-0.1cm,yshift=0.075cm]lg3.base west);")
w(r"\node[anchor=base east,font=\scriptsize,text=muted,inner sep=0pt] (lg2) at ([xshift=-0.85cm]lg3.base west) {not significant};")
w(r"\path (lg2.west) ++(-0.16,0.06) coordinate (d2);")
w(r"\node[anchor=base east,font=\scriptsize,text=muted,inner sep=0pt] (lg1) at ([xshift=-0.5cm]lg2.base west) {Holm-adjusted $p<0.05$};")
w(r"\path (lg1.west) ++(-0.16,0.06) coordinate (d1);")
w(rf"\fill[white] (d1) circle ({R_DOT + 0.032:.3f}); \fill[acc] (d1) circle ({R_DOT:.3f});")
w(rf"\fill[white] (d2) circle ({R_DOT + 0.032:.3f}); \filldraw[fill=white,draw=acc,line width=0.75pt] (d2) circle ({R_DOT * 0.84:.3f});")

w(r"\end{tikzpicture}")
w(r"\end{document}")
OUT.write_text("\n".join(out) + "\n")
hdr = "panel              | column                 | model            | effect [95% CI] (* Holm p < 0.05); two-mark rows: circle first, diamond second"
OUT.with_suffix(".values.txt").write_text(hdr + "\n" + "\n".join(rec) + "\n")
print(f"wrote {OUT} ({len(out)} lines) and {OUT.with_suffix('.values.txt').name}")
print("axes:", {P["title"]: (P["lo"], P["hi"]) for P in PANELS})
