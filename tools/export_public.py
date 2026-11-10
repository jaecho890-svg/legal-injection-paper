#!/usr/bin/env python3
"""
export_public.py - build the redacted public release of this repository.

The raw records stay unedited in the private repository. This copies what the paper releases
(fixtures, harness, analysis code, docs, the paper, raw results and run logs) into a separate
folder and redacts personal data on the way:

  * every email address           -> <redacted-email>
    (Claude-route records can contain the signed-in account's address, which the CLI wrapper
    injects; see docs/ISOLATION.md. No fixture uses an email address.)
  * home-folder paths /Users/<name> or /home/<name> -> /Users/<redacted>
  * the name a model made out of that account address -> the author's published name
    (a few Fable 5.1 memo headers, and the judge records and logs that quote them)

After copying it scans the whole export again and fails if any email address, home path or
account name is left.

  python3 tools/export_public.py [--out release/legal-injection-paper-public] [--zip]

The output folder is git-ignored. Review it before publishing anywhere.
"""
import argparse
import json
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HOME = re.compile(r"/(Users|home)/(?!<redacted>)[A-Za-z0-9._-]+")
TEXT_EXT = {".json", ".jsonl", ".md", ".csv", ".txt", ".py", ".tex", ".bib", ".log", ".out", ".swift", ".sh",
            ".css", ".js", ".html"}

INCLUDE = ["README.md", "CONTRIBUTING.md", "LICENSE", "LICENSE-DATA.md", ".gitignore", "docs", "paper", "common", "tools", "tests",
           "review/fixture_review_2026-11-08.json", "campaign_logs", "site"]
STUDIES = ["kestrel-injection-study", "interpretive-drift-study", "ip-assignment-study", "dd-pipeline-study"]
SKIP_PARTS = {"__pycache__", ".git", "results_mock", "results_calib", "dist", "preview"}
SKIP_NAMES = {"probe_report.json", "commit.log", "launchd-commit.out", "launchd-api-daily.out"}


def wanted(p: pathlib.Path) -> bool:
    return not (set(p.parts) & SKIP_PARTS) and p.name not in SKIP_NAMES and not p.name.endswith((".tmp", ".pyc"))


def sources():
    for item in INCLUDE + STUDIES:
        p = ROOT / item
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and wanted(f.relative_to(ROOT)):
                    yield f


# The author's public contact address stays in the files that present the work (README, paper,
# citation file). Everywhere else, including the raw records where the CLI wrapper injected it,
# it is redacted like any other address.
AUTHOR_EMAIL = "jae.cho.890@gmail.com"
AUTHOR_FILES = {"README.md", "paper/main.tex", "paper/main.pdf", "paper/README.md", "CITATION.cff",
                "tools/export_public.py"}
_current = {"rel": ""}

# In a few outputs a model run through the CLI turned the account address the wrapper showed it into
# a name and wrote that name into its memo header. The export replaces it with the author's
# published name, and counts each replacement in the report.
ACCOUNT_NAME = re.compile(r"\bJae\s+Cho\b")
PUBLISHED_NAME = "Jay Cho"


def _personal(addr):
    """No-reply addresses (commit attribution, GitHub no-reply) are not personal data."""
    a = addr.lower()
    if a == AUTHOR_EMAIL and _current["rel"] in AUTHOR_FILES:
        return False
    return not (a.startswith("noreply@") or a.endswith("@users.noreply.github.com"))


def redact(text):
    n_e = sum(_personal(m) for m in EMAIL.findall(text)); n_h = len(HOME.findall(text))
    text = EMAIL.sub(lambda m: "<redacted-email>" if _personal(m.group(0)) else m.group(0), text)
    text = HOME.sub(lambda m: f"/{m.group(1)}/<redacted>", text)
    text, n_n = ACCOUNT_NAME.subn(PUBLISHED_NAME, text)
    return text, n_e, n_h, n_n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "release" / "legal-injection-paper-public"))
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    files = changed = emails = homes = names = 0
    report = []
    for src in sources():
        rel = src.relative_to(ROOT)
        _current["rel"] = rel.as_posix()
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        files += 1
        if src.suffix in TEXT_EXT:
            text = src.read_text(errors="surrogateescape")
            new, n_e, n_h, n_n = redact(text)
            if n_e or n_h or n_n:
                changed += 1; emails += n_e; homes += n_h; names += n_n
                report.append({"file": str(rel), "emails": n_e, "home_paths": n_h, "names": n_n})
                if src.suffix == ".json":
                    json.loads(new)  # redaction must keep JSON valid
            dst.write_text(new, errors="surrogateescape")
        else:
            shutil.copy2(src, dst)
    (out / "REDACTION_REPORT.json").write_text(json.dumps(
        {"files": files, "files_changed": changed, "emails_redacted": emails, "home_paths_redacted": homes,
         "names_replaced": names, "changed": report}, indent=1))
    # independent re-scan of the whole export
    left = []
    for f in out.rglob("*"):
        if f.is_file() and f.suffix in TEXT_EXT and f.name != "REDACTION_REPORT.json":
            _current["rel"] = f.relative_to(out).as_posix()
            t = f.read_text(errors="ignore")
            if any(_personal(m) for m in EMAIL.findall(t)) or HOME.search(t) or ACCOUNT_NAME.search(t):
                left.append(str(f.relative_to(out)))
    print(f"{files} files exported to {out}; {changed} redacted ({emails} emails, {homes} home paths, "
          f"{names} names)")
    if left:
        print("FAILED: personal data left in", left[:10]); sys.exit(1)
    print("re-scan: no email addresses, home paths or account names left")
    if a.zip:
        z = out.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(out.parent))
        print(f"zip: {z} ({z.stat().st_size // 1_000_000} MB)")


if __name__ == "__main__":
    main()
