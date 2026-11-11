"""The paper and data pages, and the files offered for download."""
import hashlib
import re
import sys

from .core import DIST, ROOT, esc, fail, long_date
from .source import has
from .studies import table, th

# (source in the repository, name on the site, what it is)
DOWNLOADS = (
    ("paper/main.pdf", "paper.pdf", "The working paper"),
    ("paper/figures/figure1.values.txt", "figure1-values.txt", "Every value plotted in Figure 1"),
    ("docs/RESULTS.md", "results.md", "Results across the four studies, with the tables behind the paper"),
    ("docs/FIXTURES.md", "fixtures.md", "What each fictional case file contains and how it was built"),
    ("docs/VALIDATION_2026-11-10.md", "validation-2026-11-10.md", "The two recomputation passes and the corrections"),
    ("kestrel-injection-study/results_v2/analysis/summary.md", "contract-review-summary.md",
     "Contract review: every cell, with intervals and p-values"),
    ("kestrel-injection-study/results_v2/analysis/cells.json", "contract-review-cells.json",
     "Contract review: the same cells, machine-readable"),
    ("kestrel-injection-study/results_v2/analysis/judge_agreement.md", "contract-review-judge-agreement.md",
     "Contract review: agreement between the two automated judges"),
    ("kestrel-injection-study/results_v2/analysis/human_agreement.md", "contract-review-human-agreement.md",
     "Contract review: agreement between the judge and the human coder"),
    ("interpretive-drift-study/results_v2/analysis/summary.md", "interpretive-drift-summary.md",
     "Interpretive drift: every arm, model and case"),
    ("interpretive-drift-study/results_v2/analysis/trajectories_mean.csv", "interpretive-drift-trajectories.csv",
     "Interpretive drift: mean P after each evidence item"),
    ("ip-assignment-study/results_v2/analysis/summary.md", "ip-assignment-summary.md",
     "IP assignment: every arm, model and anchor"),
    ("dd-pipeline-study/results_v2/analysis/summary.md", "due-diligence-summary.md",
     "Due-diligence pipeline: every configuration"),
    ("dd-pipeline-study/results_v2/analysis/judge_agreement.md", "due-diligence-judge-agreement.md",
     "Due-diligence pipeline: agreement between the two automated judges"),
)
VALIDATION_LOG = next(name for src, name, _ in DOWNLOADS if src.startswith("docs/VALIDATION"))
STUDIES = (
    ("Contract review", "kestrel-injection-study/", "contract-review-summary.md"),
    ("Interpretive drift", "interpretive-drift-study/", "interpretive-drift-summary.md"),
    ("IP assignment", "ip-assignment-study/", "ip-assignment-summary.md"),
    ("Due-diligence pipeline", "dd-pipeline-study/", "due-diligence-summary.md"),
)
COMMANDS = (
    ("Run the unit tests", "python3 -m unittest discover -s tests"),
    ("Check the fixtures against their specifications", "python3 tools/validate_fixtures.py"),
    ("Confirm each model route answers in isolation", "python3 -m common.probe --models opus-5.5,haiku-5.5 --mark-verified"),
    ("Dry-run the contract-review experiment",
     "python3 kestrel-injection-study/harness/experiment.py run --models opus-5.5,haiku-5.5 --reps 5 --dry-run"),
)


def size(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(round(n / 1e3), 1)} kB"


def write_downloads():
    """Copy the public files, redacting with the repository's own exporter, then scan them again."""
    sys.path.insert(0, str(ROOT / "tools"))
    import export_public as ex
    out = DIST / "downloads"
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for src, name, desc in DOWNLOADS:
        p = ROOT / src
        if not p.is_file():
            fail("download source missing: " + src)
        data = p.read_bytes()
        if p.suffix != ".pdf":
            ex._current["rel"] = src
            text = ex.redact(data.decode("utf-8"))[0]
            left = ([m for m in ex.EMAIL.findall(text) if ex._personal(m)] + ex.HOME.findall(text)
                    + ex.ACCOUNT_NAME.findall(text))
            if left:
                fail("personal data left in download " + name)
            data = text.encode("utf-8")
        (out / name).write_bytes(data)
        items.append(dict(name=name, desc=desc, bytes=len(data), sha=hashlib.sha256(data).hexdigest()))
    (out / "SHA256SUMS").write_text("".join(f'{i["sha"]}  {i["name"]}\n' for i in items))
    return items


# ---- paper -----------------------------------------------------------------

def sentence_case(s):
    words = s.split()
    out = [w if (i == 0 or w.isupper() or words[i - 1].endswith("?")) else w.lower() for i, w in enumerate(words)]
    return " ".join(out)


def copy_block(cid, label, text, wrap=False):
    return (f'<div class="cite"><div class="bar"><h3>{label}</h3>'
            f'<button type="button" class="btn quiet small needs-js" data-copy="{cid}">Copy</button></div>'
            f'<pre id="{cid}"{" class=" + chr(34) + "wrapit" + chr(34) if wrap else ""}>{esc(text)}</pre></div>')


def paper(S, cfg):
    full = f'{S["title"]} {S["subtitle"]}'
    link = cfg["arxiv_url"] or cfg["site_url"]
    bib = ("@misc{cho2026steer,\n"
           f"  title  = {{{{{full}}}}},\n"
           "  author = {Cho, Jay},\n  year   = {2026},\n  month  = nov,\n  note   = {Working paper}"
           + (f",\n  url    = {{{link}}}" if link else "") + "\n}")
    apa = f"Cho, J. (2026). {sentence_case(full)} [Working paper]." + (f" {link}" if link else "")
    # AGLC4 working paper form: Author, 'Title' (Working Paper, Full Date) <URL>. No closing full stop.
    aglc = f"{S['author']}, '{full}' (Working Paper, {long_date(S['updated'])})" + (f" <{link}>" if link else "")
    posted = long_date(cfg["first_posted"]) if cfg["first_posted"] else "Not yet posted"
    arxiv = (f'<a href="{esc(cfg["arxiv_url"])}">{esc(cfg["arxiv_url"])}</a>' if cfg["arxiv_url"]
             else "Submission pending")
    meta = (("Author", f'{esc(S["author"])}, {esc(S["affil"].lower())}'),
            ("Status", "Working paper, not peer reviewed"), ("First posted", posted),
            ("Manuscript updated", f'{long_date(S["updated"])}, commit <code>{esc(S["hash"])}</code>'),
            ("arXiv", arxiv), ("Licence", esc(cfg["paper_licence"])))
    dl = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in meta)
    head = (f'<meta name="citation_title" content="{esc(full)}">\n'
            f'<meta name="citation_author" content="Cho, Jay">\n'
            '<meta name="citation_publication_date" content="2026/11">\n'
            + (f'<meta name="citation_pdf_url" content="{esc(cfg["site_url"].rstrip("/"))}/downloads/paper.pdf">\n'
               if cfg["site_url"] else ""))
    body = f"""<div class="wrap pagehead">
<p class="eyebrow">Working paper, {esc(S["date"])}</p>
<h1>{esc(S["title"])}</h1>
<p class="sub">{esc(S["subtitle"])}</p>
<div class="cta"><a class="btn primary" href="../downloads/paper.pdf">Download the PDF</a><a href="../#results">See the results</a></div>
</div>
<div class="wrap">
<section class="block abstract"><h2>Abstract</h2><p>{esc(S["abstract"])}</p></section>
<section class="block"><h2>Status</h2><dl class="rows">{dl}</dl>
<p class="muted small after">{esc(S["thanks"])}</p>
<p class="small">The numbers were recomputed from the raw records twice. <a href="../downloads/{VALIDATION_LOG}">Read the validation log</a>.</p></section>
<section class="block" id="cite"><h2>How to cite</h2>
{copy_block("aglc", "AGLC", aglc, True)}
{copy_block("apa", "APA", apa, True)}
{copy_block("bib", "BibTeX", bib)}
</section>
</div>"""
    return body, head


# ---- data ------------------------------------------------------------------

def data(S, cfg, items):
    has(S, *[c for _, c in COMMANDS])
    cov = next((x for b in S["validation"] if b[0] == "ul" for x in b[1] if x.startswith("Coverage:")), None)
    m = cov and re.search(r"([\d,]+) reviews \(([\d,]+) judged\); drift ([\d,]+) parsed conversations \((\d+) "
                          r"unparseable\); IP ([\d,]+) parsed \((\d+) unparseable\) plus (\d+) pipeline runs; "
                          r"([\d,]+) judged DD items", cov)
    if not m:
        fail("record counts not found in the validation log")
    when = next(re.search(r"\d{4}-\d\d-\d\d", b[1])[0] for b in S["validation"] if b[0] == "h1")
    counts = (f"{m[1]} reviews, {m[2]} judged", f"{m[3]} conversations parsed, {m[4]} unparseable",
              f"{m[5]} conversations parsed, {m[6]} unparseable, and {m[7]} pipeline runs", f"{m[8]} judged items")
    srows = [f'<tr><th scope="row">{a}</th><td class="t">{c}</td><td class="t"><code>{folder}</code></td>'
             f'<td class="t"><a href="../downloads/{f}">{f}</a></td></tr>'
             for (a, folder, f), c in zip(STUDIES, counts)]
    stable = table("Raw records by study",
                   "<tr>" + th("Study") + th("Raw records") + th("Folder in the repository")
                   + th("Analysis summary") + "</tr>", srows, ' class="nocap"')
    drows = [f'<tr><th scope="row"><a href="../downloads/{i["name"]}">{i["name"]}</a></th>'
             f'<td class="t">{esc(i["desc"])}</td><td class="n">{size(i["bytes"])}</td>'
             f'<td class="t"><span class="hash">{i["sha"][:16]}</span></td></tr>' for i in items]
    dtable = table("Files to download",
                   "<tr>" + th("File") + th("Contents") + th("Size", num=True) + th("SHA-256, first 16") + "</tr>",
                   drows, ' class="nocap"')
    repo = cfg["repo_url"].replace("https://", "")
    if cfg["repo_public"]:
        where = f'<a href="{esc(cfg["repo_url"])}">{esc(repo)}</a>'
        issue = f' or <a href="{esc(cfg["repo_url"])}/issues">open an issue</a>'
    else:
        where = f"{esc(repo)}. The repository opens when the paper is announced"
        issue = ""
    doi = cfg["zenodo_doi"]
    archive = f'<a href="https://doi.org/{esc(doi)}">doi:{esc(doi)}</a>' if doi else "DOI pending"
    lic = lambda v: esc(v) if v else "To be confirmed before release"
    meta = (("Repository", where), ("Archived copy", archive), ("Paper licence", lic(cfg["paper_licence"])),
            ("Code licence", lic(cfg["code_licence"])), ("Data licence", lic(cfg["data_licence"])))
    dl = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in meta)
    cmds = "".join(copy_block(f"cmd{i}", esc(label), cmd) for i, (label, cmd) in enumerate(COMMANDS))
    mail = f'mailto:{esc(S["email"])}?subject=Error%20report%20on%20the%20working%20paper'
    return f"""<div class="wrap pagehead">
<h1>Data and code</h1>
<p class="sub">Fixtures, prompts, harness, analysis code and raw records, so that every number on this site can be recomputed by someone else.</p>
</div>
<div class="wrap">
<section class="block"><h2>Where it lives</h2><dl class="rows">{dl}</dl></section>
<section class="block"><h2>Raw records</h2>{stable}
<p class="note">Counts are from the recomputation of {long_date(when)}. Raw records are never edited; the public copy removes email addresses and home-folder paths and replaces one account name with the author's.</p></section>
<section class="block" id="downloads"><h2>Downloads</h2>{dtable}
<p class="note">Checksums for every file: <a href="../downloads/SHA256SUMS">SHA256SUMS</a>. Check with <code>shasum -a 256 -c SHA256SUMS</code>.</p></section>
<section class="block"><h2>Reproduce</h2><p>From a checkout of the repository. A dry run calls no model and costs nothing.</p>
<div class="after">{cmds}</div></section>
<section class="block" id="report"><h2>Report an error</h2>
<p>If a number here does not match the raw records, or a claim goes further than the data, <a href="{mail}">write to the author</a>{issue}. Confirmed errors are fixed in the manuscript.</p>
<p>To cite the paper or the data, use the entries on the <a href="../paper/#cite">paper page</a>.</p></section>
</div>"""

