# Companion site

A static site for the working paper: results, the paper, data and code, and the corrections log.
It is generated from the manuscript and the analysis outputs, so the site cannot drift from the paper.

`dist/` is generated and ignored by git. The built site is served by GitHub Pages from the `gh-pages` branch of the public repository, at <https://jaecho890-svg.github.io/legal-injection-paper/>.

## Build

From the repository root, with Python 3 and no extra packages:

```bash
python3 site/build.py
```

This writes `site/dist/`:

| Path | What it is |
|---|---|
| `index.html` | Results: the headline figure, cohort numbers, every study as a plot and a table, approach, limits |
| `paper/index.html` | Abstract, PDF, status, how to cite (AGLC, APA, BibTeX) |
| `data/index.html` | Where the repository lives, raw records by study, downloads with SHA-256 sums, how to reproduce, how to report an error |
| `corrections/index.html` | The two validation passes and all corrections, from `docs/VALIDATION_2026-11-10.md` |
| `downloads/` | The PDF, figure values, results and fixtures notes, the validation log, the analysis summaries and `SHA256SUMS` |
| `assets/` | One stylesheet, one script, self-hosted IBM Plex fonts |

## Preview

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory site/dist
```

Then open http://127.0.0.1:4173/. All internal links are relative, so the site also works from a subfolder such as GitHub Pages.

## What it reads

| Source | Used for |
|---|---|
| `paper/main.tex` | Title, author, abstract, counts, models, limits, future work |
| `paper/figures/figure1.values.txt` | The headline figure and the per-study plots |
| Analysis summaries | The per-study tables |
| `docs/VALIDATION_2026-11-10.md` | The corrections page |
| `site/config.json` | Links, dates and licences that the manuscript does not hold |

## config.json

A `null` value renders as plain text saying the thing is pending. It never renders as a dead link.

| Field | Meaning | When `null` |
|---|---|---|
| `site_name` | Brand in the header | required |
| `site_url` | Public address, used in the citation when there is no arXiv link and in the scholar PDF tag | both left out |
| `arxiv_url` | Link to the arXiv listing | "Submission pending" |
| `first_posted` | ISO date the paper was first posted | "Not yet posted" |
| `zenodo_doi` | DOI of the archived copy | "DOI pending" |
| `repo_url` | Repository address | required |
| `repo_public` | `true` makes the repository a link | `false` prints the address as text with "opens when the paper is announced" |
| `paper_licence`, `code_licence`, `data_licence` | Licence names | "To be confirmed before release" |

## What the build refuses to do

The build stops with an error when:

- a fact written by hand in `site/gen/` no longer appears in the manuscript (each one is checked with `has()`);
- the manuscript contains LaTeX the converter does not recognise;
- visible text contains an em dash, an en dash or a backslash;
- a download still contains a personal email address or a home directory path after redaction.

Fix the source, not the output.

## Layout

```
site/
  build.py        entry point
  config.json     links, dates, licences
  gen/            core.py (shell, plot cell), source.py (reads the paper),
                  studies.py (plots and tables), home.py, pages.py
  src/            style.css, site.js
  fonts/          IBM Plex Sans and Mono (SIL Open Font Licence, see OFL.txt)
  dist/           generated, ignored
```

The script is optional. Without it every table and every panel is still on the page; it adds sorting, the model highlight, the panel switches, copy buttons and the theme choice.

## Publishing

The site is built in a clone of the public repository, so the footer names a commit readers can open.

1. Commit the change on `main` of the public repository.
2. Run `python3 site/build.py` there and check the footer shows that commit.
3. Replace the contents of the `gh-pages` branch with `site/dist/` plus an empty `.nojekyll` file, and push it.

## Still to set in config.json

1. `arxiv_url` and `first_posted`, once the paper is posted.
2. `zenodo_doi`, once the archive has one.
