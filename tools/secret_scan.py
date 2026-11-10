#!/usr/bin/env python3
"""
secret_scan.py - refuse to commit anything that looks like a credential.

Scans the files staged for commit (default) or every tracked file (--all) for API-key and
token patterns, and for key files by name. Installed as the git pre-commit hook by
`python3 tools/secret_scan.py --install-hook`.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATTERNS = {
    "OpenRouter key": re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "Anthropic key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}|\bAQ\.[A-Za-z0-9_-]{30,}"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Assigned secret": re.compile(r"(?i)\b(?:api[_-]?key|secret|token)\s*=\s*['\"]?[A-Za-z0-9_.-]{24,}"),
}
BAD_NAMES = re.compile(r"(^|/)(\.?env(\..*)?|.*\.env|auth\.json|credentials.*)$")


def files(all_tracked: bool):
    cmd = ["git", "ls-files"] if all_tracked else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--install-hook", action="store_true")
    a = ap.parse_args()
    if a.install_hook:
        hook = ROOT / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexec python3 tools/secret_scan.py\n")
        hook.chmod(0o755)
        print(f"installed {hook}")
        return
    hits = []
    for f in files(a.all):
        if BAD_NAMES.search(f):
            hits.append(f"{f}: file name looks like a credentials file")
            continue
        p = ROOT / f
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        text = p.read_text(errors="ignore")
        for label, pat in PATTERNS.items():
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{f}:{line}: possible {label}")
    if hits:
        print("Secret scan FAILED - nothing was committed:\n  " + "\n  ".join(hits))
        sys.exit(1)
    print(f"secret scan: {len(files(a.all))} files clean")


if __name__ == "__main__":
    main()
