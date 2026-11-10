# Validation run, 2026-11-10

Two independent recomputations of paper/main.tex (at 99bec72d) from the raw records. The findings and
the corrections made are in `docs/VALIDATION_2026-11-10.md`.

Pass 1 (Claude Opus 5.5, Claude Code), run from this folder with the repository root as the first argument:

- `pass1.py ROOT OUT` recomputes every Kestrel cell, drift row, IP row, DD group, the kappas and the
  coverage counts from the raw records. It uses its own parser and seed 7. Outputs: `p1a.json`
  (Kestrel, kappa, coverage) and `p1b.json` (drift, IP, DD).
- `compare.py ROOT p1a.json p1b.json` compares Pass 1 with the analysis outputs.
- `precise.py ROOT p1a.json p1b.json` recomputes every Holm family with a borderline p using
  100,000 permutations (its print label says 200k by mistake). Output: `precise.out`.
- `audit1.py`, `audit2.py` and `audit3.py` run the claim-by-claim checks. `audit3.out` holds the
  annotation, drift-direction, gloss-rewrite, IP and DD checks.

Pass 2 (GPT-6 Astra, reasoning effort xhigh, Codex CLI 0.166.0, read-only sandbox, web search off):

- `codex_prompt.md` is the prompt, `codex_pass2.md` the report and `codex_pass2.log` the full log.
