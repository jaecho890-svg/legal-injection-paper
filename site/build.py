#!/usr/bin/env python3
"""Build the companion site into site/dist. Standard library only.

    python3 site/build.py

Every number on the site is read from the manuscript (paper/main.tex), the figure values file,
the analysis summaries and the validation log. Hand-written sentences are checked against the
manuscript, so the build fails when the paper and the site disagree.
"""
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen import core, home, pages, source  # noqa: E402

FORBIDDEN = {"—": "em dash", "–": "en dash", "\\": "backslash"}


def visible(html):
    html = re.sub(r"<(script|style|pre)\b.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def main():
    cfg = json.loads((core.SITE / "config.json").read_text())
    S = source.load()
    if core.DIST.exists():
        shutil.rmtree(core.DIST)
    (core.DIST / "assets").mkdir(parents=True)
    shutil.copy(core.SITE / "src/style.css", core.DIST / "assets/style.css")
    shutil.copy(core.SITE / "src/site.js", core.DIST / "assets/site.js")
    shutil.copytree(core.SITE / "fonts", core.DIST / "assets/fonts")
    items = pages.write_downloads()

    name = cfg["site_name"]
    paper_body, paper_head = pages.paper(S, cfg)
    out = {
        "index.html": core.page(
            S, cfg, "results", "", f'{S["title"]} {name}',
            "Four experiments on 17 models: can text written by the opposing party steer an AI legal reviewer?",
            home.home(S)),
        "paper/index.html": core.page(
            S, cfg, "paper", "../", f"The paper. {name}",
            "Abstract, status, PDF and citation for the working paper.", paper_body, paper_head),
        "data/index.html": core.page(
            S, cfg, "data", "../", f"Data and code. {name}",
            "Raw records, analysis outputs, checksums and the commands that reproduce the results.",
            pages.data(S, cfg, items)),
        "corrections/index.html": core.page(
            S, cfg, "corrections", "../", f"Corrections. {name}",
            "What two independent recomputations of the paper found, and what was changed.",
            pages.corrections(S)),
    }
    for rel, html in out.items():
        text = visible(html)
        for ch, label in FORBIDDEN.items():
            if ch in text:
                i = text.index(ch)
                core.fail(f"{label} in the visible text of {rel}: ...{core.ws(text[max(i - 60, 0):i + 40])}...")
        p = core.DIST / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html)
    host = urlparse(cfg["site_url"] or "").hostname
    if host and not host.endswith(".github.io"):
        (core.DIST / "CNAME").write_text(host + "\n")  # GitHub Pages reads the custom domain from this file
    print(f"built {len(out)} pages and {len(items)} downloads into {core.DIST.relative_to(core.ROOT)}")


if __name__ == "__main__":
    main()
