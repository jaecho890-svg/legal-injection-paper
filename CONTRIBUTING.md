# Contributing

## Before every commit

```bash
python3 -m unittest discover -s tests
```

```bash
python3 tools/validate_fixtures.py
```

```bash
python3 tools/secret_scan.py
```

The secret scan runs automatically as a pre-commit hook once installed (`python3 tools/secret_scan.py --install-hook`; the hook is per-clone, so install it after cloning). It blocks commits containing API keys or tokens, or files named like `env`, `.env` or `auth.json`.

## Rules

- **No credentials in the repo, ever.** Keys live in a file outside the repo and are loaded into the shell (`set -a; . ~/path/to/env; set +a`). If a key is committed by accident, rotate it first and clean the history second.
- **No real client material.** Fixtures are synthetic and must stay that way.
- **Fixture changes are reviewed.** A changed fact pattern changes the experiment. Note it in the commit message, keep `DRAFT` until legal review, and never edit a case that already has reported results: copy it to a new file instead.
- **Don't edit pilot outputs.** `*/results/` and `*_findings.md` are the frozen pilot record.
- **Results are data.** `results_v2/` folders and `campaign_logs/` are committed every day by `tools/daily_commit.sh` (scheduled with launchd), so every call and every queue event is in git history. Mock outputs (`results_mock/`) are never committed. Raw records are never edited after the fact; redaction for a public data release is a separate export step (see docs/ISOLATION.md).
