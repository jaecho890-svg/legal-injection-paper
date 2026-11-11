# Adversarial framing and prompt injection in AI legal review

This repository holds the research code and synthetic fixtures for a study of whether text one party places in legal documents can shift the conclusions of the opposing party's AI reviewer. It covers four studies: contract review (Kestrel), interpretive drift on balanced disputes, IP-assignment correspondence, and a cheap-summariser/strong-decider due-diligence pipeline.

**Site:** <https://adversarialrecord.org/> (results, the paper, data and downloads). **Paper:** [paper/main.pdf](paper/main.pdf), source in [paper/main.tex](paper/main.tex) (see [paper/README.md](paper/README.md)). **Results record:** [docs/RESULTS.md](docs/RESULTS.md).

The public copy of this repository is built by `tools/export_public.py`, which removes email addresses and home-folder paths from the raw records, replaces the name a model made out of the account address with the author's published name, and lists every file it changed in `REDACTION_REPORT.json`.

**Start here:** [docs/ONBOARDING.md](docs/ONBOARDING.md) covers setup, logins, probes and running. [docs/ISOLATION.md](docs/ISOLATION.md) records what each model route sees. [docs/FIXTURES.md](docs/FIXTURES.md) covers the case files and how to write new ones.

## Independence and authorship

An independent, open-source research project by Jay Cho (<jae.cho.890@gmail.com>), a practising solicitor admitted in New South Wales, Australia. It was built on my own time with my own resources and not reviewed by my employer. The views expressed here are exclusively my own and should not be attributed to any entity I am associated with.

No model provider or legal-technology vendor (including Anthropic, OpenAI, Google, NVIDIA or OpenRouter) sponsors, partners with or endorses this work. Every case file is fictional, written for this study; no client or confidential information is used. I designed, directed and reviewed the study, and used Claude (Anthropic), in Claude Code, as a research and drafting assistant; the paper's "Use of AI tools" section gives the details. Nothing here is legal advice.

Requirements: Python 3.9 or later. Standard library only, nothing to install.

## Status (2026-11-06)

| | |
|---|---|
| Harness | v2 complete: CLI and API routes, replicates, blinded judge, statistics, human-validation export, offline tests |
| Models probed and verified | Claude Code CLI: Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5, Opus 4.8. Codex CLI: GPT-6.1 Sol, GPT-6.1 Terra, GPT-6 Astra, GPT-6 Sol, GPT-6 Luna, GPT-5.6 Sol, GPT-5.6 Terra, GPT-5.6 Luna. API: Gemini 3.6 Flash; OpenRouter Nemotron 3 Ultra, dots.3 note, Xing 4.0 |
| Throughput (measured) | Kestrel review: Claude 33–93 s per call, GPT 30–58 s; about 4–6 calls a minute per route with 4–6 in parallel |
| Fixtures | 4 new cases (2 drift, 1 IP, 1 DD) and real-PDF Kestrel variants; all reviewed 2026-11-08 ([docs/FIXTURE_REVIEW_2026-11-08.md](docs/FIXTURE_REVIEW_2026-11-08.md)) |
| Results | Core-five campaign and phase 2 complete (lone-flag DD room, real-PDF injection, last-position drift arms, three DRAFT cases at full scale): see [docs/RESULTS.md](docs/RESULTS.md). API-model subset growing to 20 reps nightly. Raw records in each study's `results_v2/`, run logs in `campaign_logs/` (committed daily) |
| Human validation | 200-row blinded Kestrel sheet (`kestrel-injection-study/results_v2/annotation/sheet.csv`) coded blind by the author; agreement with the judge is reported in [docs/RESULTS.md](docs/RESULTS.md) |

## What v2 changed from the pilot

| Pilot gap | v2 |
|---|---|
| Runs went through Claude Code subagents; model versions unrecorded | Exact model ids from `common/models.json`, each route isolated and probed. Every call is logged: request, reply, model, flags, tokens, timing, and a fingerprint of the harness code. |
| One run per condition | `--reps` (20 for reported results), bootstrap CIs, permutation tests, Holm correction |
| Regex scorers, one of which fired on clean runs | A blinded judge model codes each output; a blinded export for human validation gives Cohen's kappa |
| Kestrel robustness may only reflect the playbook | `NO_PLAYBOOK` cell; skew measured against the same model's clean control |
| Drift: client note and per-item glosses changed together | Separate note, gloss and order arms |
| Drift and IP: single call, so the model could read ahead | True multi-turn protocol by default |
| IP "adversarial" arm changed facts while claiming "same facts" | `curated` (changes the record) vs `assert_only` (keeps every honest item); anchors differ only in the anchor paragraph; a positive-control case |
| IP and DD probes run by hand | Runnable commands, including the full-text baseline |

## Quick commands

```bash
python3 -m unittest discover -s tests
```

```bash
python3 tools/validate_fixtures.py
```

```bash
python3 -m common.probe --models opus-5.5,haiku-5.5 --mark-verified
```

```bash
python3 kestrel-injection-study/harness/experiment.py run --models opus-5.5,haiku-5.5 --reps 5 --dry-run
```

Each study runs `run`, then `judge` (Kestrel and DD only), then `analyze`. See the onboarding guide for every flag.

## Layout

```
common/        backends (API + CLI), runner/ledger, probe, stats, annotation, mock, models.json
tools/         validate_fixtures.py, secret_scan.py
tests/         offline tests, including a fake API server
docs/          onboarding, isolation, fixtures, results, validation
site/          generator for the companion site (see site/README.md)
<study>/       corpus/ (fixtures), harness/ (experiment.py + pilot scripts), results/ (frozen pilot)
```

## Licence

Code is under the MIT licence ([LICENSE](LICENSE)). The fixtures, prompts, raw records, logs, documentation and the paper are under CC BY 4.0 ([LICENSE-DATA.md](LICENSE-DATA.md)). The fonts in `site/fonts/` are IBM Plex, under the SIL Open Font Licence.

All fixtures are fictional. Nothing in this repository is legal advice.
