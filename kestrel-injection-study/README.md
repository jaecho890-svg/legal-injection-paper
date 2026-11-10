# Kestrel adversarial-framing study

Does text an adversary places in one party's legal document skew the **opposing party's AI reviewer**? A defensive robustness experiment on fully synthetic Project Kestrel SPA fixtures.

| File | What it is |
|---|---|
| `01_technique_taxonomy.md` | Literature distillation (insane-research): two-family taxonomy of injection vs framing/harness manipulation, cited effect sizes, defenses. |
| `02_research_design.md` | Hypotheses, conditions (6 document × 2×2 defense), objective skew scoring. |
| `03_findings.md` | Pilot results and honest interpretation + limitations. |
| `corpus/issues.json` | 16-issue ground truth (playbook-correct buyer positions). |
| `corpus/base_documents.json` | Clean seller documents (from the fixtures). |
| `corpus/variants/` | Generated document conditions C0/A1/A2/B1/B2/B3. |
| `harness/build_variants.py` | Layers framing/injection onto the clean base (deterministic). |
| `harness/reviewer_prompt.py` | Builds the buyer-reviewer prompt per defense cell. |
| `harness/run_experiment.py` | Backend-agnostic runner (subagent / Anthropic API / manual). |
| `harness/score.py` | Parses verdicts → per-issue skew → `results/summary.md`. |
| `results/` | Prompts, raw reviewer outputs, `scores.csv`, `summary.md`. |

**Pilot result (2026-11-04):** 6/6 runs held all 16 positions (skew 0/32). A frontier reviewer with its own playbook detected and rejected both explicit injection and combined framing. This is a floor case — see `03_findings.md` for the levers (weaker models, adaptive attacks, open-judgment issues, GUARD_OFF) that the harness is built to pull next.

Quick start: `python3 harness/build_variants.py && python3 harness/run_experiment.py --plan pilot --backend manual` then feed `results/prompts/*.json` to a reviewer, save replies to `results/runs/<run_id>.response.txt`, and `python3 harness/score.py`.

All fixtures are fictional. The harness is a measurement instrument for a defender's robustness question, not a payload kit.
