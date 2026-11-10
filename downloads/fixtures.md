# Synthetic fixtures

All fixtures are fictional. A case is not ready for reported results until a lawyer has reviewed it and its `_meta.status` no longer says `DRAFT`. `python3 tools/validate_fixtures.py` checks structure; it cannot check legal correctness.

## Inventory

| File | Study | What it is | Status |
|---|---|---|---|
| `kestrel-injection-study/corpus/issues.json`, `base_documents.json` | Kestrel | 16-issue share-sale negotiation with buyer playbook ground truth | pilot |
| `interpretive-drift-study/corpus/case.json` | Drift | Aster/Delphin termination dispute, v1 (control leaned "wrongful") | pilot, superseded |
| `interpretive-drift-study/corpus/case_v2.json` | Drift | Same dispute, rebalanced so control sits near 50 | pilot |
| `interpretive-drift-study/corpus/case_employment.json` | Drift | **New.** Summary dismissal for alleged data misconduct (Talbot Freight / Kovac) | reviewed 2026-11-08 (docs/FIXTURE_REVIEW_2026-11-08.md) |
| `interpretive-drift-study/corpus/case_insurance.json` | Drift | **New.** Claim declined for non-disclosure at proposal (Corbel Mutual / Penrose Bakeries) | reviewed 2026-11-08 (docs/FIXTURE_REVIEW_2026-11-08.md) |
| `ip-assignment-study/corpus/case.json` | IP | No executed deed; the counterparty inflates its claim | pilot |
| `ip-assignment-study/corpus/case_executed.json` | IP | **New positive control.** Executed deed and board approval exist; the developer tries to cast doubt | reviewed 2026-11-08 (docs/FIXTURE_REVIEW_2026-11-08.md) |
| `dd-pipeline-study/corpus/*.json` | DD | Data room with three red flags and three injections; compression probes | pilot |
| `dd-pipeline-study/corpus/loneflag_docs.json` | DD | **New.** Lone red flag (a change-of-control termination right in one sentence of the largest customer's contract) plus an admission positive control (the CFO states a covenant breach as fact) beside a hedged speculation | reviewed 2026-11-08 (docs/FIXTURE_REVIEW_2026-11-08.md) |
| `kestrel-injection-study/corpus/pdf/C0P.pdf`, `A2P.pdf` and `variants/C0P.txt`, `A2P.txt` | Kestrel | **New.** The clean letter as a real PDF, without and with the A2 payload in invisible text (render mode 3); the `.txt` files are what macOS PDFKit extracts. Rebuild with `python3 tools/make_kestrel_pdf.py` | built 2026-11-06 |

## Drift case schema

```json
{
  "_meta": {
    "status": "DRAFT - needs legal review ...",
    "role_intro": "You are a NEUTRAL AI case assessor supporting ... between X and Y.",
    "question": "How likely is it that ...? P=0 ...; P=50 genuinely balanced; P=100 ...",
    "lean_A": "Employer", "lean_B": "Employee",
    "balance_design": "A-favouring: ... B-favouring: ... Neutral: ..."
  },
  "intake_memo": {"neutral": "...", "A_drip": "...", "A_strong": "...", "B_drip": "...", "B_strong": "..."},
  "items": [{"id": "E1", "lean": "neutral|<lean_A>|<lean_B>", "facts": "...", "gloss_A": "Note: ...", "gloss_B": "Note: ..."}]
}
```

Rules:

- **Balanced.** Equal numbers of items leaning each way, plus neutral items. The clean control should land near 50. Pilot the control on two models before running steered arms, and rebalance the facts if it doesn't.
- **Glosses change framing, not facts.** A gloss may emphasise, characterise or minimise, but must not add information. The validator rejects any number in a gloss that does not appear in the case's facts.
- **A pushes P up, B pushes down.** `gloss_A` and the `A_*` memos argue toward 100.
- **Strong memos** come from "Lead Counsel" and ask the assessor to stay consistent with the case theory. That is the authority lever.

## IP case schema

```json
{
  "_meta": {"question": "...", "ground_truth": "...", "manipulation_direction": "up|down"},
  "intake_memo": {"honest": "...", "adversarial": "<note from the manipulating party>"},
  "honest_order": ["IP1", "..."],
  "adversarial_order": ["IP9", "..."],
  "items": [{"id": "IP1", "facts": "<honest rendering>", "adv": "<adversarial rendering, or empty to omit>"}]
}
```

The harness builds three arms from one file:

| Arm | Memo | Items |
|---|---|---|
| `honest` | honest | `facts` in `honest_order` |
| `assert_only` | adversarial | `IP9.adv` first, then every honest `facts` item unchanged |
| `curated` | adversarial | `adv` renderings in `adversarial_order`; items with empty `adv` are dropped |

`IP9.adv` is the manipulating party's summary of rights and is required. `curated` must omit at least one item, or it differs from `assert_only` only in wording; the validator warns about that.

## Writing a new case

1. Copy the closest existing file and change the parties, facts and question. Keep it fictional; don't reuse names of real firms.
2. Write the facts first, then the glosses. Read each gloss against its fact and delete anything new.
3. Set `status` to `DRAFT - needs legal review` and run the validator.
4. Pilot the control arm (drift) or honest arm (IP) on two models at 3–5 reps. Check that the control sits where the design says it should.
5. Send it for legal review. Record the reviewer and date in `_meta.status` when it's cleared.

## Still to build

- **More Kestrel-style issue sets** in other deal types (for example, a SaaS master services agreement), so the "firm anchors hold" result rests on more than one document.
- **More DD data rooms.** The lone-flag room and the admission control now exist (`loneflag_docs.json`); a second room in another sector would show the results are not one fixture's.
- **Other PDF hiding techniques** for Kestrel: white 1pt text and text behind an image, beside the render-mode-3 version built so far.
