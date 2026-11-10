"""Everything the site shows is read here from the manuscript and the analysis outputs."""
import re
import subprocess

from .core import ROOT, WORDS, detex, fail, fnum, slug, ws

NUM = r"[+\-\u2212]?\d+\.\d+"


def need(m, what):
    if not m:
        fail("could not find " + what)
    return m


# ---- LaTeX tables ----------------------------------------------------------

def table_env(tex, label):
    for env in re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", tex, re.S):
        if "\\label{tab:%s}" % label in env:
            return env
    fail("no table labelled tab:" + label)


def caption(tex, label):
    env = table_env(tex, label)
    i = j = env.index("\\caption{") + 9
    depth = 1
    while depth:
        depth += (env[j] == "{") - (env[j] == "}")
        j += 1
    return detex(env[i:j - 1])


def tex_rows(tex, label):
    env = table_env(tex, label)
    body = need(re.search(r"\\begin\{tabularx?\}[^\n]*\n(.*?)\\end\{tabularx?\}", env, re.S), "tabular in " + label)[1]
    body = re.sub(r"\\(?:top|mid|bottom)rule|\\addlinespace(?:\[[^\]]*\])?|\\cmidrule(?:\([^)]*\))?\{[^}]*\}", "", body)
    rows = []
    for raw in body.split("\\\\"):
        raw = ws(raw)
        if not raw:
            continue
        g = re.match(r"\\multicolumn\{\d+\}\{\w+\}\{\\emph\{(.+?)\}\}$", raw)
        rows.append(("group", g[1]) if g else ("row", [c.strip() for c in raw.split("&")]))
    return rows


def nums(cell):
    """All numbers in a cell as (text, starred)."""
    return [(a, bool(b)) for a, b in re.findall(r"\$?(%s)\$?(\\sig)?" % NUM, cell)]


def data_rows(rows):
    return [r for k, r in rows if k == "row" and r[0] not in ("", "Model", "Group")]


def table_models(tex):
    out = []
    for group, seg, reps in data_rows(tex_rows(tex, "models")):
        for part in seg.split(";"):
            m = re.match(r"(.+?)\s*\((.+?)\)$", part.strip())
            names, route = (m[1], m[2]) if m else (part, "Direct API")
            route = "OpenRouter API" if route == "OpenRouter" else route
            for n in names.split(","):
                out.append(dict(name=n.strip(), slug=slug(n), group=group, route=route, reps=int(reps)))
    return out


def table_naming(tex):
    out = []
    for r in data_rows(tex_rows(tex, "naming")):
        names = r[0].split(" / ")
        cols = [c.split(" / ") for c in r[1:]]
        for i, n in enumerate(names):
            out.append(dict(name=n, cells=[detex(c[i] if len(c) > 1 else c[0]) for c in cols]))
    return out


def table_api(tex):
    out, group = [], None
    cell = re.compile(r"\$(%s)\$\s*\$\[(%s),\s*(%s)\]\$,\s*\$p\s*([=<])\s*([\d.]+)\$" % (NUM, NUM, NUM))
    for kind, r in tex_rows(tex, "api"):
        if kind == "group":
            group = r
            continue
        if r[0] in ("", "Model"):
            continue
        cs = []
        for c in r[2:4]:
            m = need(cell.match(c), "Table 3 cell: " + c)
            cs.append(dict(v=m[1], lo=m[2], hi=m[3], op=m[4], p=m[5]))
        out.append(dict(name=r[0], group=group, control=r[1], cells=cs))
    return out


def table_drift(tex):
    rows = tex_rows(tex, "drift")
    head = [h for h in rows[0][1][1:]]
    return head, [dict(name=r[0], cells=[nums(c)[0] for c in r[1:]]) for r in data_rows(rows)]


def table_ip(tex):
    blocks, cur = {}, None
    for kind, r in tex_rows(tex, "ip"):
        if kind == "group":
            cur = blocks.setdefault(r, [])
        elif r[0] not in ("", "Model"):
            cur.append(dict(name=r[0], cells=[nums(c) for c in r[1:]]))
    return blocks


# ---- figure values file ----------------------------------------------------

def figure_values():
    out = {}
    lines = (ROOT / "paper/figures/figure1.values.txt").read_text().splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        panel, col, model, rest = [p.strip() for p in line.split("|", 3)]
        marks = [dict(v=a, lo=b, hi=c, star=bool(d))
                 for a, b, c, d in re.findall(r"(%s)\s*\[\s*(%s),\s*(%s)\]\s*(\*?)" % (NUM, NUM, NUM), rest)]
        if not marks:
            fail("values file line not understood: " + line)
        out.setdefault(panel, {}).setdefault(col, {})[model] = marks
    return out


# ---- markdown --------------------------------------------------------------

def md_blocks(text):
    """Small markdown reader: headings, paragraphs, bullet lists, pipe tables."""
    blocks, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("h%d" % level, line.lstrip("# ").strip()))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip()[1:-1])]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows[0], rows[1:]))
        elif line.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or (lines[i].startswith("  ") and lines[i].strip())):
                if lines[i].startswith("- "):
                    items.append(lines[i][2:].strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            blocks.append(("ul", items))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "- ")):
                para.append(lines[i].strip())
                i += 1
            blocks.append(("p", " ".join(para)))
    return blocks


def rate(cell):
    """'0.10 [0.02, 0.40]' to (0.10, 0.02, 0.40); a bare rate has no interval."""
    m = re.match(r"(\d\.\d+)(?:\s*\[(\d\.\d+),\s*(\d\.\d+)\])?", cell)
    if not m:
        return None
    return tuple(float(x) if x else None for x in m.groups())


def dd_summary():
    text = (ROOT / "dd-pipeline-study/results_v2/analysis/summary.md").read_text()
    out, name = {}, None
    for b in md_blocks(text):
        if b[0] == "h2":
            name = b[1].split(" (")[0]
        elif b[0] == "table" and name:
            out[name] = [dict(zip(b[1], r)) for r in b[2]]
    coded = need(re.search(r"Coded items: (\d+)", text), "DD coded items")[1]
    return out, int(coded)


# ---- everything ------------------------------------------------------------

def load():
    tex = (ROOT / "paper/main.tex").read_text()
    flat = ws(tex)
    S = dict(tex=flat, readme=ws((ROOT / "README.md").read_text()))

    m = need(re.search(r"\\title\{(.+?)\\\\\s*\\large\s+(.+?)\}", tex, re.S), "title")
    S["title"], S["subtitle"] = ws(m[1]), ws(m[2])
    m = need(re.search(r"\\author\{(.+?)\\thanks\{(.+?)\}\\\\\s*\\small\s+(.+?)\\\\\s*\\small\\texttt\{(.+?)\}\}",
                       tex, re.S), "author block")
    S["author"], S["thanks"], S["affil"], S["email"] = ws(m[1]), detex(m[2]), ws(m[3]), m[4]
    S["date"] = need(re.search(r"\\date\{(.+?)\}", tex), "date")[1]

    ab = ws(need(re.search(r"\\begin\{abstract\}(.+?)\\end\{abstract\}", tex, re.S), "abstract")[1])
    parts = re.split(r"\((\d)\)~", ab)
    if len(parts) != 9:
        fail("abstract does not have four numbered findings")
    last, tail = parts[8].split(" The threat to", 1)
    closing, release = ("The threat to" + tail).split(" All fixtures", 1)
    S["abstract_intro"] = detex(parts[0])
    S["findings"] = [detex(x) for x in (parts[2], parts[4], parts[6], last)]
    S["closing"] = detex(closing)
    S["release"] = detex("All fixtures" + release)
    S["abstract"] = detex(ab)

    m = need(re.search(r"(\w+) studies, (\d+) models and about ([\d,]+) assessments", S["abstract"]), "cohort")
    S["n_studies"], S["n_models"], S["n_assess"] = WORDS[m[1].lower()], int(m[2]), m[3]
    m = need(re.search(r"One contract issue set, (\w+) drift cases, (\w+) IP cases and (\w+) data rooms", flat),
             "scenario counts")
    S["scen"] = [1] + [WORDS[w] for w in m.groups()]

    S["models"] = table_models(tex)
    S["naming"] = table_naming(tex)
    S["api"] = table_api(tex)
    S["drift_head"], S["drift"] = table_drift(tex)
    S["ip"] = table_ip(tex)
    S["fig"] = figure_values()
    S["cap"] = {k: caption(tex, k) for k in ("models", "naming", "api", "drift", "ip")}
    S["dd"], S["dd_coded"] = dd_summary()

    m = need(re.search(r"Across (\d+) model--case cells.*?last-A was positive in (\d+), last-B negative in (\d+), "
                       r"first-A negative in (\d+) and first-B positive in (\d+)", flat), "order counts")
    S["order"] = [int(x) for x in m.groups()]

    lim = need(re.search(r"\\section\{Limitations\}.*?\\begin\{itemize\}(.+?)\\end\{itemize\}", tex, re.S),
               "limitations")[1]
    S["limits"] = [(detex(t).rstrip("."), detex(x))
                   for t, x in re.findall(r"\\item\s+\\textbf\{(.+?)\}\s*(.+?)(?=\\item|\Z)", lim, re.S)]
    fw = need(re.search(r"\\paragraph\{Future work\.\}\s*(.+?)\n\s*\n", tex, re.S), "future work")[1]
    S["future"] = [re.sub(r"^and ", "", x.strip()) for x in detex(fw).rstrip(".").split(";")]
    S["future"] = [x[0].upper() + x[1:] for x in S["future"]]

    val_md = (ROOT / "docs/VALIDATION_2026-11-10.md").read_text()
    S["validation"] = md_blocks(val_md)

    out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%cs %h", "--", "paper/main.tex"],
                         capture_output=True, text=True).stdout.split()
    if len(out) != 2:
        fail("could not read the manuscript commit from git")
    S["updated"], S["hash"] = out
    check(S)
    return S


def has(S, *snippets):
    """Hand-written facts on the site must still be in the manuscript or the README."""
    for s in snippets:
        if s not in S["tex"] and s not in S["readme"]:
            fail("the manuscript no longer says: " + s)


def check(S):
    if len(S["models"]) != S["n_models"]:
        fail("Table 1 lists %d models; the abstract says %d" % (len(S["models"]), S["n_models"]))
    if len(set(m["slug"] for m in S["models"])) != len(S["models"]):
        fail("duplicate model in Table 1")
    names = {m["name"] for m in S["models"]}
    cr = S["fig"]["Contract review"]
    for row in S["api"]:
        if row["name"] not in names:
            fail("Table 3 model not in Table 1: " + row["name"])
        for cell, col in zip(row["cells"], ("Hidden instruction", "Combined framing")):
            f = cr[col][row["name"]][0]
            if any(abs(fnum(cell[k]) - fnum(f[k])) > 1e-9 for k in ("v", "lo", "hi")):
                fail("Table 3 and the figure values disagree for %s, %s" % (row["name"], col))
            sig = cell["op"] == "<" or float(cell["p"]) < 0.05
            if sig != f["star"]:
                fail("significance mark disagrees for %s, %s" % (row["name"], col))
            cell["star"] = sig
    for t in (S["drift"], *S["ip"].values()):
        for r in t:
            if r["name"] not in names:
                fail("unknown model in a results table: " + r["name"])
    if len(S["limits"]) < 3 or len(S["future"]) < 3:
        fail("limitations or future work did not parse")
