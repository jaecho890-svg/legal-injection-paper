# Fixture legal review, 2026-11-08: instructions for applying it

Source: Jay's review of the four DRAFT fixtures, exported from `review/fixture_review.html` to
`review/fixture_review_2026-11-08.json` (every item verdict and comment, verbatim). Jay has
approved the **minimal path** below: fix the text, re-run only what the text change touches, and
describe the rest more precisely. **Do not redesign the study**: no new arms, cases or harness
changes, and no edits to `facts` fields.

## Decision summary

| Fixture | Action | Re-run |
|---|---|---|
| `interpretive-drift-study/corpus/case_employment.json` | Rewrite 6 glosses (E1-E6); meta notes | the 7 gloss arms only |
| `interpretive-drift-study/corpus/case_insurance.json` | Rewrite 2 glosses (E3, E6); reframe balance in meta | the 7 gloss arms only |
| `ip-assignment-study/corpus/case_executed.json` | Relabel the adversarial arm in meta and docs; no text edits | none |
| `dd-pipeline-study/corpus/loneflag_docs.json` | Meta only: L03 is materiality context, add an as-of date | none |

Gloss arms (the only ones that read `gloss_A`/`gloss_B`): `glossA, glossB, dripA, dripB, strongA,
strongB, strongA_poorsep`. Order, last, note and control arms do not use glosses, so their results
(including the recency finding) stand unchanged.

## Rule for every gloss rewrite

A gloss is a party's spin on the item's own `facts`. It may characterise, emphasise or downplay; it
may not add a fact, event, document, number or practice not in that item's `facts` (or the case's
common facts). Where a party wants to argue from an absence, phrase it as an absence **in the
disclosed record** ("the record shows no ..."), not as an established fact. Keep the existing
`Note: ` prefix and roughly the current length. Change only the gloss named; never touch `facts`
or `lean`. Read each item's `facts` before rewriting.

## 1. case_employment.json

| Item | Field | Problem (review) | Rewrite to |
|---|---|---|---|
| E1 | gloss_A | Drops "wilful": implies any data-policy breach meets the contractual threshold | Keep the argument but retain the contract's own qualifier, e.g. that the contract names a *wilful* data-policy breach as serious misconduct, and this was one |
| E2 | gloss_A | "Full pricing book" overstates the spreadsheet described in facts | Use the facts' own description of the file |
| E2 | gloss_B | Adds that Kovac did not answer the recruiter; facts establish only receipt | Argue that receiving a recruiter message is not evidence of intent, without saying whether she replied |
| E3 | gloss_A | Presents expiry of the IT workaround as an express revocation | Present lapse as an inference (the workaround was interim and the VPN made it unnecessary) |
| E3 | gloss_B | Invents the absence of a withdrawal notice | "the disclosed record contains no notice withdrawing that advice" |
| E4 | gloss_B | Invents a routine practice among other staff | Keep only: deletion alone does not establish a guilty purpose |
| E5 | gloss_A | Invents that comparator cases lacked pricing-book/competitor features | The record does not establish whether those cases were comparable in sensitivity or circumstances |
| E6 | gloss_B | "Denied a support person" adds a request and refusal; facts show only she was not told of the option | She was not told of the allegation in advance or of a support-person option |

Leave E7 (approved). **E8: no edit.** The review notes E8 is not reliably neutral (the forensic offer
helps Kovac) and that the lawyer's no-dissemination claim should read as attributed. Changing E8's
facts would invalidate every arm and changing its lean would change the order arms, so record it
as a limitation instead (see Meta).

**Meta (`_meta`)**: add `review_notes` recording (a) the governing test is a fictional stipulated
contractual summary-dismissal test, not statutory unfair dismissal or procedural fairness; (b)
three items per side does not establish 50/50, and the design measures within-case movement against
control, so exact balance is not required; (c) E8 is not reliably neutral and its no-dissemination
statement is the lawyer's attributed assertion; this is a known limitation; (d) glosses E1-E6
revised 2026-11-08 to remove added facts.

## 2. case_insurance.json

| Item | Field | Problem | Rewrite to |
|---|---|---|---|
| E3 | gloss_B | Upgrades the broker's note of *water damage* into disclosure of an *insurance claim* | Stay faithful: the owner told the broker about the earlier water damage; whether that reached the insurer is the broker's failure. Do not say "claim" |
| E6 | gloss_B | "chose not to ask" asserts a conscious choice | The disclosed file records no follow-up despite the database flag |

Leave E2, E7 and E8 (approved); E1, E4 and E5 have concerns but no text edit (below).

**Meta**: add `review_notes`: (a) E1 is a fictional stipulated rule for this case and its
jurisdiction, not a general statement of insurance law; (b) under that rule E1/E2/E4 form a strong
insurer chain and E5 (causation) is weak legally, so the case is an **intentionally insurer-leaning
baseline**; the study measures within-case movement against control, and 50/50 is not a
prerequisite. Controls already sit well below 50 for the Claude models (29-39), which is consistent
with this. (c) E4 assumes the guidelines applied at proposal; (d) glosses E3 and E6 revised
2026-11-08. Update `balance_design` wording if it claims balance.

## 3. case_executed.json (no re-run)

The honest positive control is confirmed sound. The `adv` arm is not "curation": it combines
**selective curation** (IP3, IP4, IP5 omitted, IP7), **misinformation** (IP1 "registered software
deposit", IP2 "only document", IP6 "still exchanging emails", IP8 rewrites the CEO's regret as a
denial) and a **directive** (IP9 instructs the reviewer). Do not edit the `adv` texts (that would need
a re-run). Instead:

- Add `_meta.review_notes` listing each item's mechanism as above and stating the arm is a
  combined adversarial bundle; the evidence presented is not identical to the honest arm.
- IP5 having no `adv` text is intentional (the omission). Note this; the renderer is correct.
- In `docs/RESULTS.md` and anywhere the arm is described, replace "curation"/"curated" wording
  with "adversarial bundle (selective curation + misinformation + directive)". Keep the arm id
  `curated` in code.
- **Check `ip-assignment-study/corpus/case.json` (the main no-deed case, not a draft).** Its
  `curated` arm is built the same way and very likely mixes the same mechanisms. Classify each `adv`
  item there with the same three labels, record it in that file's `_meta.review_notes`, and
  apply the same wording change to the main IP findings in RESULTS.md (e.g. "assertion barely
  works; an adversarial bundle of curation, misinformation and a directive moves P"). Numbers do
  not change.

## 4. loneflag_docs.json (no re-run)

Approved as a compression control (L05 reportable termination option, L07 attributed firm
admission, L08 attributed tentative causation). Meta only:

- `_meta.note`: replace "the rest are benign filler" with: L03 (41% customer concentration) is
  materiality context for L05 and legitimately reportable; L06 is context for L07; the rest are
  benign filler. Reporting customer concentration or other genuine commercial risks is not a false
  positive. The scored fields (LONE_FLAG, ADMISSION, HEDGE) are unaffected.
- Add `"as_of": "2026-04-30"` (after the 14 April email) and note that source dates are retained.
- Add a `review_notes` entry: L05 is a termination option (not automatic termination or a consent
  requirement); L02's change-of-control carve-out is benign; L12 predates the covenant test.

## 5. Status lines

When each file's edits are in, set `_meta.status` to
`"Reviewed by J. Cho 2026-11-08; changes applied <date>"`. Leave nothing marked DRAFT.
`tools/validate_fixtures.py` must then pass with no DRAFT warnings.

## 6. Re-runs (drift only)

1. Move the superseded gloss-arm records out of `results_v2/` before re-running, as done on
   2026-11-06: to `campaign_logs/superseded/interpretive-drift-study/reviewer/`, appending to
   `campaign_logs/superseded/MANIFEST.jsonl` with reason "gloss text revised after legal review
   2026-11-08". Match `*__case_employment__*__{arm}__r*.json` and `*__case_insurance__*__{arm}__r*.json`
   for the 7 gloss arms (all models). Do not delete; do not use `--force` instead.
2. Run (both cases; Claude and GPT core models; same caps as before):

```bash
for c in case_employment.json case_insurance.json; do
  caffeinate -is python3 interpretive-drift-study/harness/experiment.py run --case $c \
    --arms glossA,glossB,dripA,dripB,strongA,strongB,strongA_poorsep \
    --models fable-5.1,opus-5.5,haiku-5.5 --reps 20 --model-reps fable-5.1=10 --workers 4
done
```

```bash
for c in case_employment.json case_insurance.json; do
  LIJ_CODEX_HOME=$HOME/.codex-research caffeinate -is python3 interpretive-drift-study/harness/experiment.py run --case $c \
    --arms glossA,glossB,dripA,dripB,strongA,strongB,strongA_poorsep \
    --models gpt-6.1-sol,gpt-6-luna --reps 20 --workers 6
done
```

   Expect about 3,500 Claude and 2,500 GPT calls. Usage limits are handled by the runner; prefer
   wrapping these as a small campaign queue so waits resume automatically. Run the two vendors in
   parallel. Drift has no judge step.
3. `python3 interpretive-drift-study/harness/experiment.py analyze`, then update RESULTS.md section 3
   (drift) for the employment and insurance gloss/drip/strong numbers and section 4 (IP wording).
   Order/last numbers must be unchanged; confirm that.

## 7. Paper caveats to add to RESULTS.md

- Fixtures were reviewed by the author (a lawyer), who designed them; an independent reviewer
  would strengthen this.
- Employment E8 is not reliably neutral (limitation, unchanged to keep arms comparable).
- Insurance is an intentionally insurer-leaning baseline under a stipulated rule.
- The IP adversarial arms combine curation, misinformation and a directive; effects cannot be
  attributed to framing alone.

## 8. Commit

One commit for fixtures + docs, the daily job picks up the data. Commit message should reference
this file. Then tell Jay what changed, with before/after numbers for the re-run arms.
