#!/bin/bash
# daily_commit.sh - commit and push the campaign logs and raw results once a day.
#
# Run by launchd (~/Library/LaunchAgents/com.jaecho.legal-injection.daily-commit.plist)
# at 23:45 and on wake if that time was missed. Safe to run by hand at any time:
#   bash tools/daily_commit.sh
# Stages only campaign_logs/ and each study's results_v2/, never code or anything else
# in the working tree. The pre-commit secret scan still runs. Output: campaign_logs/commit.log
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p campaign_logs
exec >>campaign_logs/commit.log 2>&1

stamp() { date '+%Y-%m-%dT%H:%M:%S'; }
echo "[$(stamp)] daily commit start"

# wait out a git operation already in progress (another commit, a fetch)
for _ in 1 2 3 4 5 6; do [ -e .git/index.lock ] || break; sleep 20; done

paths=(campaign_logs)
for d in */results_v2; do [ -d "$d" ] && paths+=("$d"); done
git add -A -- "${paths[@]}" || { echo "[$(stamp)] git add failed"; exit 1; }

if git diff --cached --quiet; then
  echo "[$(stamp)] nothing new to commit"
else
  counts=$(python3 - <<'EOF'
import glob, json
ok = err = 0
for f in glob.glob("*/results_v2/*/*.json"):
    try:
        s = json.load(open(f)).get("status")
    except Exception:
        continue
    ok += s == "ok"; err += s == "error"
print(f"{ok} ok / {err} error result files")
EOF
)
  files=$(git diff --cached --name-only | wc -l | tr -d ' ')
  git commit -q -m "Daily log snapshot $(date '+%Y-%m-%d'): ${files} files changed; ${counts}

Automated by tools/daily_commit.sh: campaign logs and raw results_v2 records.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || { echo "[$(stamp)] commit failed (see above)"; exit 1; }
  echo "[$(stamp)] committed $(git log -1 --format=%h): ${files} files; ${counts}"
fi

# push, including any earlier snapshot that failed to push
for attempt in 1 2 3; do
  if git push -q origin main; then
    echo "[$(stamp)] pushed to origin/main"
    exit 0
  fi
  echo "[$(stamp)] push attempt ${attempt} failed; retrying in 60s"
  sleep 60
done
echo "[$(stamp)] push FAILED; commit kept locally, next run will push it"
exit 1
