#!/bin/sh
# Build figure1.pdf, main.pdf and main.bbl from the analysis outputs, main.tex and refs.bib.
# arXiv does not run BibTeX, so main.bbl is committed and uploaded with main.tex and figure1.pdf.
# Needs Python 3 and Tectonic (https://tectonic-typesetting.github.io); set TECTONIC to its path if
# it is not on PATH. Fails, copying nothing, if LaTeX reports any warning or overfull box.
set -eu
cd "$(dirname "$0")"
TECTONIC="${TECTONIC:-tectonic}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Figure 1: generated from the analysis outputs, then compiled on its own.
python3 figures/make_figure1.py >/dev/null
mkdir "$tmp/fig"
cp figures/figure1.tex "$tmp/fig/"
(cd "$tmp/fig" && "$TECTONIC" -X compile --keep-logs figure1.tex >/dev/null 2>"$tmp/fig/err") \
  || { cat "$tmp/fig/err"; exit 1; }
# The standalone class always notes that shell escape is off; any other warning fails the build.
if grep -E "Warning|^!" "$tmp/fig/figure1.log" | grep -v "Package shellesc Warning: Shell escape disabled"; then
  echo "figure warnings above; nothing copied"; exit 1
fi
cp "$tmp/fig/figure1.pdf" "$tmp/"

# The paper. Tectonic is XeTeX-based: the \pdfoutput=1 line (which tells arXiv to use pdfLaTeX)
# would make hyperref load its pdfTeX driver, so this build drops that one line.
grep -v '^\\pdfoutput=1$' main.tex > "$tmp/main.tex"
cp refs.bib "$tmp/"
(cd "$tmp" && "$TECTONIC" -X compile --keep-intermediates --keep-logs main.tex >/dev/null 2>"$tmp/tectonic.err") \
  || { cat "$tmp/tectonic.err"; exit 1; }
# Overfull boxes are content running past a margin; they fail the build like warnings.
if grep -i "warning" "$tmp/main.blg"; then echo "BibTeX warnings above; nothing copied"; exit 1; fi
if grep -E "Warning|^!|Overfull" "$tmp/main.log"; then echo "LaTeX warnings above; nothing copied"; exit 1; fi
cp "$tmp/figure1.pdf" "$tmp/main.pdf" "$tmp/main.bbl" .
echo "built figure1.pdf, main.pdf and main.bbl, no LaTeX warnings"
