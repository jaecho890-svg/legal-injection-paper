# Paper

`main.tex`, `refs.bib`, `main.bbl` and `figure1.pdf` are the arXiv source (cs.CL / cs.CY), written
from `docs/RESULTS.md`. Every number in the paper comes from that file or the analysis outputs it
cites. `main.pdf` is the compiled paper. Figure 1 is generated from the analysis outputs by
`figures/make_figure1.py`, which also writes `figures/figure1.values.txt`, every plotted value and
its 95% interval. Table 3's rows were generated from
`kestrel-injection-study/results_v2/analysis/cells.json` on 2026-11-09.

## Build

```bash
TECTONIC=~/.local/share/tectonic-0.17.0/tectonic sh paper/build.sh
```

`build.sh` regenerates Figure 1, compiles it and then the paper in a temporary folder, copies back
`figure1.pdf`, `main.pdf` and `main.bbl`, and fails without copying anything if LaTeX reports a
warning or an overfull box. Where `tectonic` is on PATH, plain `sh paper/build.sh`
works. On the campaign machine (an Intel Mac, where Homebrew has no Tectonic bottle) the official
release binary is in `~/.local/share/tectonic-0.17.0/`.

`latexmk -pdf main.tex` and Overleaf (pdfLaTeX) also work. The paper uses only standard packages
(geometry, lmodern, amsmath, booktabs, caption, graphicx, float, tabularx, xcolor, natbib,
hyperref; the figure source also uses TikZ). Figure 1 is placed with `[H]` so it always sits
between the Results introduction and Section 4.1. Do not run
`tectonic main.tex` directly: the first line, `\pdfoutput=1`, is for arXiv's pdfLaTeX and breaks
XeTeX-based engines, which is why `build.sh` drops it for its own build.

## Submitting to arXiv

Upload `main.tex`, `main.bbl` and `figure1.pdf`. arXiv does not run BibTeX, so the references come
from `main.bbl`: re-run `build.sh` after any change to `refs.bib`, the citations or the analysis
outputs. Checked 2026-11-10: those three files alone compile to the same text as `main.pdf`, with no
warnings. (Tectonic runs BibTeX itself, so the check copies the three files to an empty folder and
replaces `\bibliography{refs}` with `\input{main.bbl}` in the copy, as arXiv's no-BibTeX build
effectively does.) Do not upload `figures/figure1.tex`: it is a LaTeX document of its own and could be taken
for the main file.

## Before submission

- Endorsement: since 21 January 2026 a first-time arXiv submitter needs a personal endorsement
  from an established author in the category (cs.CL).
- Licence: MIT for code (`LICENSE`), CC BY 4.0 for fixtures, data, documentation and the paper
  (`LICENSE-DATA.md`), chosen 2026-11-10.
- AI use: disclosed in the paper's "Use of AI tools" section and in the fixture and limitations
  text, as arXiv's policy requires.
- References: all 25 checked on 2026-11-09. The original 11 arXiv entries against the arXiv API (one
  author list corrected); the four classic entries against Crossref, JSTOR and Open Library (no
  changes); the ten related-work additions against the arXiv API and the ACL Anthology, with every
  claim about them taken from their abstracts. See the header of `refs.bib`.
- Numbers: on 2026-11-09 all four analyses were re-run from the raw records and reproduced the
  reported results (drift's bootstrap "mean drift" column, which the paper does not report, varies
  in its last digit). Every Table 4 cell was checked against the drift summary; one wrong
  significance mark was removed. On 2026-11-10 two independent recomputations from the raw records
  (Claude, and GPT-6 Astra through the Codex CLI) checked every number and claim. Their 25
  corrections are listed in `docs/VALIDATION_2026-11-10.md`, and the scripts and reports are in
  `campaign_logs/validation_2026-11-10/`.
- Public data release: `python3 tools/export_public.py --zip` builds the redacted copy in
  `release/` (git-ignored) and re-scans it; review it before uploading.
- Optional strengtheners listed in docs/RESULTS.md: a second human coder on 50 items, a harder DD
  injection case, more Kestrel issue sets.
- Re-check numbers if any analysis is re-run: `docs/RESULTS.md` is the source the paper follows.
