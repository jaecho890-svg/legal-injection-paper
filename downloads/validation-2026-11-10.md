# Validation against the raw records, 2026-11-10

Two independent passes recomputed the paper's numbers and claims (paper/main.tex at 99bec72d) from
the raw per-run records. The analysis summaries were used only to locate things.

- **Pass 1** (Claude Opus 5.5 in Claude Code): its own parser and statistics (permutation tests
  with a different seed, Holm, bootstrap, κ), compared cell by cell with the analysis outputs,
  then a claim-by-claim audit. Every Holm-adjusted p between 0.01 and 0.10 was rechecked with
  100,000 permutations.
- **Pass 2** (GPT-6 Astra at extra-high reasoning effort, through the Codex CLI in a read-only
  sandbox): an independent audit of the same records, 663 checks.

Scripts, outputs and the Pass 2 report and log: `campaign_logs/validation_2026-11-10/`.

## What reproduced

- Coverage: 5,510 reviews (5,509 judged); drift 4,258 parsed conversations (82 unparseable); IP
  1,078 parsed (2 unparseable) plus 150 pipeline runs; 1,050 judged DD items; 17 models.
- Contract review: all 510 cells have the same n, mean skew and Δ. Under a different seed no
  significance call changes. Tables 2 and 3 reproduce at printed precision.
- Drift: all 299 rows have the same n, final P and Δ. Table 4's cells and stars reproduce, as do
  the order counts (22, 23, 22, 21 of 23).
- IP: all 60 rows reproduce, and Table 5 with them. Pipeline: 21–33 against 1–7. Haiku 5.5 −14.1
  (Holm p 0.042; 0.044 with 100,000 permutations), with the deed named present in 12 of 20 runs.
- Reliability: issue position κ 0.74 (raw agreement 0.98; 537 reviews, 8,592 codes); naming
  κ 0.81; DD hedge κ 0.68 and cluster κ 0.23; human κ 0.54 (132 items) and 0.91 (68 items).
- 100,000-permutation recheck: one call changes. GPT-6 Luna's dismissal-case gloss A after the
  rewrite has Holm p 0.053 in the analysis output and 0.033 with 100,000 permutations (0.026
  under Pass 1's seed). No mark in the tables or the figure changes.

## Corrections

P1 and P2 name the pass that found each one.

| # | Where | As written | In the raw records | Found by | Now |
|---|---|---|---|---|---|
| 1 | §4.1 | "Every model named framing far less often than injection" | Opus 4.8: 0.96 against 1.00. GPT-6 Sol: 0.10 against 0.10. dots.3, Gemini and Nemotron name framing more often (0.80–0.90 against 0.25–0.50) | both | Limited to the Claude models other than Opus 4.8; GPT rates added |
| 2 | §4.2 | The strong arm "moved against its own side in every model" | Strong A: 13 of 13. Strong B: 7 of 13. GPT-6 Luna −18.8*, with B | both | Stated per side |
| 3 | §4.2 | Note alone had "no meaningful effect (\|Δ\| ≤ 3.3 for every core model)" | True only on the commercial case. Up to 11.7 on the new cases (Opus, insurance, note B). All nine significant note effects go against the note's slant | both | Limited to the commercial case; the new cases and the pattern stated |
| 4 | §3.2, §4.2 | "Eight glosses" | Ten gloss texts on eight items | both | Corrected |
| 5 | §4.2 | Gloss A "lost significance for … GPT-6 Luna" | +7.3 → +5.4, Holm p 0.053 (10,000 permutations) or 0.033 (100,000) | P1 | Luna's change given as numbers only |
| 6 | §4.2 | The rewrite "shrank the affected side's effect" | Employment gloss A fell in all five core models. The rewritten employment B glosses moved models about as much as before. Re-running the insurance A-side arms with unchanged text moved estimates by up to 10.5 points and cost three cells their significance | P2 raised it, P1 quantified it | Qualified as noisy and suggestive |
| 7 | §4.2, §5, §1 | "Opus 5.5, and GPT-6.1 Sol on one case, moved against them"; "two models reacted against slanted glosses rather than with them" | Opus: 7 of 8 significant gloss or drip effects go against the slant, but employment gloss B is −5.6*, with it. Sol: 4 against (commercial A side, insurance B side), 4 with (B side on the commercial and dismissal cases) | both | Qualified |
| 8 | §4.3 | The soft anchor "roughly doubled" the bundle's effect | 2.0–2.9× | P1 | "two to three times larger" |
| 9 | §4.3 | The bundle moved the answer "just as hard the other way" | −36 to −86 in the positive control, against +5 to +25 in the no-deed case | P1 | "even further the other way, by 36 to 86 points" |
| 10 | Abstract, §1, §8 | Assertions "almost never moved the final answer" | 9 of 20 assertion cells moved significantly, 8 of them against the asserting party | P2 | "toward that party" |
| 11 | §4.4 | No pipeline "recommended proceeding" | 0 of 200 unconditional PROCEED. 44 of 100 naive-harness runs recommended PROCEED_WITH_CONDITIONS (31 of 40 Luna → Sol), against 0 of 100 hardened | both | "unconditionally"; the conditional recommendations reported |
| 12 | §4.4 | Direct readers kept the hedge in "80–100%" | Fable 5.1 on discovery: 1 of 10, hardened 9 of 10. Everyone else 80–100% | both | Exception stated |
| 13 | §4.4 | Fable 5.1 hardened in "90% of discovery runs" | 80% with normal notes, 90% with terse, 90% direct | P1 | 80–90% |
| 14 | §4.4 | Compression lost "the links between scattered documents" | Rests on the cluster field the paper excludes (κ 0.23). Deciders were coded CONNECTED in 80–100% of runs | P1 | Removed |
| 15 | §3.7 | DD red-flag, fabrication, lone-flag and admission "κ = 1.00" | Agreement 100%, but κ is undefined because both judges used one category. Laundering and recommendation κ 0.83 were not reported | both | Reworded; laundering and recommendation added |
| 16 | §3.7 | "39 … (PARTIAL or ACCEPT)" | 25 PARTIAL, 8 ACCEPT, 6 NOT_ADDRESSED | both | Label list corrected |
| 17 | §3.7 | "a deterministic random 10% sample" | The rule selects 546 reviews; 537 were second-coded. Nine API reviews were collected after the second-judge run | P2 | Stated |
| 18 | §4.1 | "Only three cells survived correction" (and Haiku 5.5 "had none") | Haiku 5.5 A2P −0.60* in the PDF family | P1 | "Outside the PDF conditions" |
| 19 | §4.1 | "No model moved toward the seller" (PDF) | 10 of 15 A2P Δ are positive (at most +0.50), none significant | both | "significantly" |
| 20 | §3.8, §6 | Fable 5.1 has "10 replicates" | Five contract-review C0 cells have 20 | P2 | Stated |
| 21 | §3.6 | Terse notes "at most 90 words" | An instruction, not a cap: at least 4 of 120 notes exceed it | P2, confirmed by P1 | "instructed to stay within 90 words" |
| 22 | §5 | dots.3 "followed the instruction almost completely" | Mean 23.9 of 32; full compliance in 8 of 20 reviews | P1 | "largely followed" |
| 23 | §5 | "vendor and model differences here were larger than the differences between attack types" | No defined measure. In the IP study the attack type mattered far more than the model | P2 (could not verify), P1 | Replaced with a statement the data support |
| 24 | §6 | The bias "makes contract-review effects conservative" | The direction is suggested, not established: the sample is small and label-stratified | P2 | "if anything, overstates" |
| 25 | Figure 1 values file | Drift and IP values printed to two decimals | The summaries give one decimal (19 of 68 estimates and 29 of 68 intervals affected) | P2 | Printed at the source's precision |

The Statistics section now states the permutation count (10,000) and the 100,000-permutation
recheck. The Use of AI tools section names both passes.

## Checked and left unchanged

- Wrapper sizes (§3.1). They come from the isolation probes (docs/ISOLATION.md), which the raw
  reviewer records do not show.
- "Calibrated P about 75–95" for the positive control. This states the design's intent, not a
  result.
- The second judge's 109 DD items. These are the complete 10% sample: no sampled item is
  missing.
