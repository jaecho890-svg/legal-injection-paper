# Onboarding

This project measures whether text one party puts into legal documents can shift the conclusions of the other party's AI reviewer. There are four studies, all on fully synthetic material:

| Study | Question | Folder |
|---|---|---|
| Kestrel | Does injected or framed text in a seller's share-sale documents move a buyer-side reviewer off its positions on 16 negotiation issues? | `kestrel-injection-study/` |
| Interpretive drift | On a genuinely balanced dispute, does slanted framing move a running probability estimate, and does the shift last as evidence accumulates? | `interpretive-drift-study/` |
| IP assignment | Can a counterparty's framing or curation of correspondence inflate (or deflate) the assessed odds that an IP assignment took effect? | `ip-assignment-study/` |
| DD pipeline | In a cheap-summariser → strong-decider pipeline, are injected instructions caught, and do hedges and scattered red flags survive compression? | `dd-pipeline-study/` |

Each study folder keeps its pilot write-up (`*_findings.md`) and pilot outputs (`results/`) unchanged for traceability. New work goes through `harness/experiment.py` and writes to `results_v2/`.

## 1. Set up (once per machine)

Requirements: macOS or Linux, Python 3.9 or later (standard library only), `git`.

**Claude models** run through your signed-in Claude Code CLI:

```bash
claude update
```

```bash
claude auth login
```

**GPT models** run through Codex, using a *separate* Codex home that contains only a login. Never point the harness at `~/.codex`: that folder's `AGENTS.md`, memories and plugins would leak into every prompt (a probe confirmed it).

```bash
mkdir -p ~/.codex-research && CODEX_HOME=~/.codex-research codex login
```

```bash
export LIJ_CODEX_HOME=~/.codex-research
```

**API models** (Gemini, OpenRouter) read keys from environment variables. Keep the key file **outside the repository** and load it only into the shell that runs experiments:

```bash
set -a; . ~/Downloads/env; set +a
```

The `.gitignore` blocks `env`, `.env` and `*.env`, but the safe habit is never to copy key files into the repo at all.

## 2. Check every model before using it

```bash
python3 -m common.probe --models fable-5.1,opus-5.5,sonnet-5.5,haiku-5.5,opus-4.8 --mark-verified
```

The probe checks that the model answers, that our system prompt is in force, that none of your own instruction files are visible, that multi-turn works, and that no tools are exposed. Only models that pass get `verified: true` in `common/models.json`, and the runner refuses unverified models. The results go to `common/probe_report.json`. [ISOLATION.md](ISOLATION.md) describes exactly what each route sees.

## 3. Check the fixtures

```bash
python3 tools/validate_fixtures.py
```

This must exit with 0 errors before any run. `DRAFT` warnings mean a case has not had legal review yet. Draft cases can be piloted, but results from them must not be reported. See [FIXTURES.md](FIXTURES.md).

## 4. Run a study

Every command takes `--dry-run`, which counts calls and sends nothing. Use it first, every time.

```bash
python3 kestrel-injection-study/harness/experiment.py run --models opus-5.5,haiku-5.5 --reps 5 --dry-run
```

The order is `run`, then `judge` (Kestrel and DD), then `analyze`. Runs resume: finished jobs are skipped, so an interrupted run can be started again with the same command. Tables land in `<study>/results_v2/analysis/summary.md`.

| Flag | Use |
|---|---|
| `--reps N` | replicates per cell (20 for reported results; 3–5 to shake out problems) |
| `--max-calls N` | refuse to start anything bigger than N calls |
| `--model-reps M=N` | cap one model's replicates, e.g. `fable-5.1=10` |
| `--sample F` | run a deterministic fraction of jobs (used for the second judge) |
| `--workers N` | parallel calls. CLI routes are subscription-limited; start at 2–4 |
| `--case FILE` | drift and IP: which case file in the study's `corpus/` |
| `--protocol single` | drift and IP: the pilot's one-call protocol, kept for comparison only |

**Quotas.** Claude and GPT through the CLIs are limited by your subscriptions. Gemini's free tier allows about 20 requests a day, and OpenRouter's about 50 a day shared across its free models, so those models can only run small, targeted subsets. Plan those by hand.

## 5. Validate the automated judge

Kestrel and DD use a judge model that codes each output without seeing the condition. The primary judge is GPT-6.1 Sol; Opus 5.5 codes a deterministic 10% sample, and `experiment.py agreement --a gpt-6.1-sol --b opus-5.5` reports inter-judge kappa. The paper needs human agreement figures:

```bash
python3 kestrel-injection-study/harness/experiment.py export-annotation --n 200
```

Give `results_v2/annotation/sheet.csv` to the coder and keep `key.json` away from them. Once they've filled in `human_label`:

```bash
python3 -m common.annotate kappa --sheet kestrel-injection-study/results_v2/annotation/sheet.csv --key kestrel-injection-study/results_v2/annotation/key.json
```

For agreement with both judges, Opus 5.5 must have coded the same reviews (`judge --judge opus-5.5 --only-annotated`; done for the 2026-11-06 sheet). Then:

```bash
python3 kestrel-injection-study/harness/experiment.py annotation-kappa --b opus-5.5
```

It writes `results_v2/analysis/human_agreement.md` with human vs GPT-6.1 Sol and human vs Opus 5.5, per field.

## 6. Long campaigns and scheduled jobs

- `tools/campaign.py --queue <name>` runs a planned queue of stages (`claude`, `gpt`, `judge-final`, and the phase-2 `claude2`, `gpt2`, `judge-final2`). It resumes finished jobs, sleeps through subscription usage limits until the stated reset (by the wall clock, so a sleeping Mac does not stretch the wait) and re-runs a crashed stage. Run it under `caffeinate -is` and keep the Mac on AC power.
- `tools/watchdog.py <queue> ...` exits with a reason when a queue finishes, dies or stalls; it logs a heartbeat to `campaign_logs/watchdog.log`.
- Two launchd jobs in `~/Library/LaunchAgents/`:
  - `com.jaecho.legal-injection.daily-commit` (23:45): `tools/daily_commit.sh` commits and pushes `campaign_logs/` and every `results_v2/`.
  - `com.jaecho.legal-injection.api-daily` (20:00): `tools/api_daily.py` adds API-model Kestrel reps within the free daily quotas, then judges and re-analyses. It reads keys from `~/.config/legal-injection/api.env` (mode 600, never in the repo) because launchd jobs cannot read `~/Downloads`.
  - Stop one with `launchctl bootout gui/$(id -u)/<label>`.
- `python3 tools/make_kestrel_pdf.py` rebuilds the real-PDF Kestrel variants (C0P, A2P) and their PDFKit text.

## 7. Ground rules

- **Synthetic only.** No client documents, real parties or confidential material, in fixtures or in prompts.
- **Never commit credentials.** Run `git diff --cached` and the secret scan in [CONTRIBUTING.md](../CONTRIBUTING.md) before every commit.
- **Mock output is not data.** `mock-*` models exist to test the plumbing.
- **Report what ran.** Every record stores the model id, route, flags, and harness fingerprint. Quote those, not what you meant to run.
- **Disclosure.** If a commercial legal-AI product is ever tested, notify the vendor before publishing (see the paper plan).

## Repository map

```
common/            shared harness: backends (API + CLI), runner/ledger, probe, stats, annotation, mock
  models.json      model aliases -> exact ids and routes; verified flags
tools/             validate_fixtures.py
tests/             offline tests (python3 -m unittest discover -s tests)
docs/              this guide, ISOLATION.md, FIXTURES.md
<study>/corpus/    synthetic fixtures
<study>/harness/   experiment.py (v2) + pilot-era scripts
<study>/results/   pilot outputs (frozen)
<study>/results_v2/ new outputs (created by runs)
```
