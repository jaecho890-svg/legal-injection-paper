"""Shared helpers: paths, text cleaning, number formatting, the plot cell and the page shell."""
import html
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
ROOT = SITE.parent
DIST = SITE / "dist"
MINUS = "\u2212"
NBSP = "\u00a0"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}


def fail(msg):
    sys.exit("build failed: " + msg)


def esc(s):
    return html.escape(str(s), quote=True)


def ws(s):
    return re.sub(r"\s+", " ", s).strip()


def slug(name):
    return name.strip().lower().replace(" ", "-")


def long_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def detex(s):
    """LaTeX fragment to plain text. Fails on anything it does not recognise."""
    s = re.sub(r"\s*\\citep?\{[^}]*\}", "", s)
    s = re.sub(r"\s*\(Table~\\ref\{[^}]*\}\)", "", s)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\\(?:textbf|emph|texttt|textit)\{([^{}]*)\}", r"\1", s)

    def math(m):
        t = m.group(1).replace("\\kappa", "kappa").replace("-", MINUS)
        return re.sub(r"\s*([<>=])\s*", r" \1 ", t).strip()

    s = re.sub(r"\$([^$]*)\$", math, s)
    s = s.replace("``", "\u201c").replace("''", "\u201d")
    s = re.sub(r"(\d)--(\d)", r"\1 to \2", s)
    s = s.replace("--", "-")
    for a, b in (("\\%", "%"), ("\\_", "_"), ("\\&", "&"), ("\\sig", "*"), ("\\ ", " "), ("~", " ")):
        s = s.replace(a, b)
    s = ws(s)
    if "\\" in s or "{" in s:
        fail("unhandled LaTeX in: " + s[:160])
    return s


def sgn(s, plus=True):
    """Signed number as text: true minus, optional plus, bare zero."""
    s = str(s).strip().replace(MINUS, "-")
    body = s.lstrip("+-")
    if float(body) == 0:
        return body
    return (MINUS if s.startswith("-") else "+" if plus else "") + body


def fnum(s):
    return float(str(s).replace(MINUS, "-").replace("+", ""))


def val(v, lo=None, hi=None, star=False, slot=True, plus=True):
    """Inner HTML for a numeric cell: value, optional interval, fixed-width star slot."""
    out = sgn(v, plus)
    if lo is not None:
        out += f' <span class="ci">[{sgn(lo, False)}, {sgn(hi, False)}]</span>'
    if slot:
        out += "*" if star else NBSP
    return out


def td(inner, v=None, cls="n"):
    dv = f' data-v="{esc(v)}"' if v is not None else ""
    return f'<td class="{cls}"{dv}>{inner}</td>'


# ---- plot cell -------------------------------------------------------------

def _pos(v, lo, hi):
    return (min(max(v, lo), hi) - lo) / (hi - lo) * 100


def tick_label(t, unit=""):
    return (sgn(str(int(t)), False) if float(t) != 0 else "0") + unit


def axis_th(title, lo, hi, ticks, unit="", extra=""):
    spans = "".join(f'<span style="left:{_pos(t, lo, hi):.2f}%">{tick_label(t, unit)}</span>' for t in ticks)
    return (f'<th class="pc" scope="col"{extra}><span class="axt">{esc(title)}</span>'
            f'<div class="axis" aria-hidden="true">{spans}</div></th>')


def plot_td(lo, hi, ticks, marks):
    """marks: dicts with v, and optionally lo, hi, on, shape ('c' or 'd'), track ('a' or 'b')."""
    two = any(m.get("track") for m in marks)
    out = [f'<td class="pc"><div class="plot{" two" if two else ""}" aria-hidden="true">']
    for t in ticks:
        out.append(f'<i class="g{" z" if t == 0 else ""}" style="left:{_pos(t, lo, hi):.2f}%"></i>')
    for m in marks:
        tr = " " + m["track"] if m.get("track") else ""
        if m.get("lo") is not None:
            a, b = _pos(fnum(m["lo"]), lo, hi), _pos(fnum(m["hi"]), lo, hi)
            out.append(f'<i class="wh{tr}" style="left:{a:.2f}%;width:{max(b - a, 0):.2f}%"></i>')
        cls = "mk" + (" d" if m.get("shape") == "d" else "") + (" on" if m.get("on") else "") + tr
        out.append(f'<i class="{cls}" style="left:{_pos(fnum(m["v"]), lo, hi):.2f}%"></i>')
    out.append("</div></td>")
    return "".join(out)


def key(*items):
    """Legend line. Each item is (mark classes or None, label)."""
    spans = []
    for cls, label in items:
        mark = f'<i class="{cls}"></i>' if cls else ""
        spans.append(f"<span>{mark}{esc(label)}</span>")
    return '<p class="key">' + "".join(spans) + "</p>"


# ---- page shell ------------------------------------------------------------

NAV = (("results", "Results", ""), ("paper", "Paper", "paper/"),
       ("data", "Data and code", "data/"), ("corrections", "Corrections", "corrections/"))
HEAD_JS = ('document.documentElement.className="js";try{var t=localStorage.getItem("theme");'
           'if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}')


def licence_line(cfg):
    def one(label, v):
        return f"{label}: {esc(v)}." if v else f"{label} licence to be confirmed before release."
    return " ".join([one("Paper", cfg["paper_licence"]), one("Code", cfg["code_licence"]),
                     one("Data", cfg["data_licence"])])


def page(S, cfg, cur, rel, title, desc, body, head=""):
    nav = "".join(
        f'<a href="{rel + href or "./"}"{" aria-current=" + chr(34) + "page" + chr(34) if k == cur else ""}>{label}</a>'
        for k, label, href in NAV)
    fonts = "".join(
        f'<link rel="preload" href="{rel}assets/fonts/ibm-plex-sans-latin-{w}-normal.woff2" as="font" '
        f'type="font/woff2" crossorigin>' for w in (400, 500))
    themes = "".join(f'<button type="button" data-theme-set="{t}">{t.capitalize()}</button>'
                     for t in ("auto", "light", "dark"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta name="color-scheme" content="light dark">
{head}<script>{HEAD_JS}</script>
{fonts}
<link rel="stylesheet" href="{rel}assets/style.css">
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="{rel or "./"}">{esc(cfg["site_name"])}</a>
<nav class="nav" aria-label="Site">{nav}</nav>
</div></header>
<main>
{body}
</main>
<footer class="foot"><div class="wrap">
<div>
<p>{esc(S["author"])}, {esc(S["affil"].lower())}. Nothing on this site is legal advice.</p>
<p>{licence_line(cfg)}</p>
<p>Built from manuscript commit <code>{esc(S["hash"])}</code> of {long_date(S["updated"])}.</p>
</div>
<div class="seg needs-js" role="group" aria-label="Colour theme">{themes}</div>
</div></footer>
<script src="{rel}assets/site.js" defer></script>
</body>
</html>
"""
