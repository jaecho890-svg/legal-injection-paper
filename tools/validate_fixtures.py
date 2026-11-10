#!/usr/bin/env python3
"""
validate_fixtures.py - structural checks on every synthetic case file, run before any experiment.

It cannot judge whether a case is legally right (that is the reviewing lawyer's job, tracked
by `_meta.status`). It catches the mistakes that silently break an experiment:
  * missing or misspelled fields, duplicate ids, orders that point at items that do not exist
  * drift cases that are not balanced (same number of items leaning each way)
  * glosses that add facts: any number in a gloss must already appear in the case's facts
    (a gloss may point back to an earlier item), because glosses are meant to change framing only
  * IP cases whose adversarial arm keeps every item (then `curated` = `assert_only`)
Exit status is non-zero if any ERROR is found; WARN lines are printed but do not fail.

  python3 tools/validate_fixtures.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NUM = re.compile(r"\d[\d,.]*")
errors, warns = [], []


def err(f, m): errors.append(f"ERROR {f.relative_to(ROOT)}: {m}")
def warn(f, m): warns.append(f"WARN  {f.relative_to(ROOT)}: {m}")


def nums(t):
    return {n.strip(".,") for n in NUM.findall(t)}


def check_drift(f, c):
    meta = c.get("_meta", {})
    if "question" not in meta:
        err(f, "_meta.question missing")
    memo = c.get("intake_memo", {})
    for k in ("neutral", "A_drip", "A_strong", "B_drip", "B_strong"):
        if not memo.get(k):
            err(f, f"intake_memo.{k} missing")
    la, lb = meta.get("lean_A", "Aster"), meta.get("lean_B", "Delphin")
    items = c.get("items", [])
    ids = [i.get("id") for i in items]
    if len(ids) != len(set(ids)):
        err(f, "duplicate item ids")
    counts = {la: 0, lb: 0, "neutral": 0}
    case_nums = set().union(*(nums(i.get("facts", "")) for i in items)) if items else set()
    for it in items:
        for k in ("id", "lean", "facts", "gloss_A", "gloss_B"):
            if not it.get(k):
                err(f, f"item {it.get('id')} missing {k}")
        if it.get("lean") not in counts:
            err(f, f"item {it.get('id')} lean {it.get('lean')!r} not in {list(counts)}")
            continue
        counts[it["lean"]] += 1
        for g in ("gloss_A", "gloss_B"):
            extra = nums(it.get(g, "")) - case_nums
            if extra:
                err(f, f"item {it['id']} {g} introduces numbers not in the facts: {sorted(extra)}")
    if counts[la] != counts[lb]:
        err(f, f"unbalanced: {counts}")
    if "role_intro" not in meta and "Aster" not in json.dumps(c):
        warn(f, "no _meta.role_intro; harness will describe the parties as Aster/Delphin")


def check_ip(f, c):
    meta = c.get("_meta", {})
    for k in ("question", "ground_truth"):
        if not meta.get(k):
            err(f, f"_meta.{k} missing")
    for k in ("honest", "adversarial"):
        if not c.get("intake_memo", {}).get(k):
            err(f, f"intake_memo.{k} missing")
    items = {i.get("id"): i for i in c.get("items", [])}
    if "IP9" not in items or not items["IP9"].get("adv"):
        err(f, "IP9 with an adversarial summary is required (used by assert_only and curated arms)")
    for order in ("honest_order", "adversarial_order"):
        for k in c.get(order, []):
            if k not in items:
                err(f, f"{order} references unknown item {k}")
    for i in items.values():
        if not i.get("facts"):
            err(f, f"item {i.get('id')} has no honest facts")
    kept = [k for k in c.get("adversarial_order", []) if k in items and items[k].get("adv", "").strip()]
    if set(c.get("honest_order", [])) <= set(kept):
        warn(f, "adversarial arm omits no item; 'curated' differs from 'assert_only' only by rewording")


def check_kestrel(f, c):
    iss = c.get("issues", [])
    ids = [i.get("id") for i in iss]
    if len(ids) != len(set(ids)):
        err(f, "duplicate issue ids")
    for i in iss:
        for k in ("id", "topic", "seller_position", "correct_buyer_position"):
            if not i.get(k):
                err(f, f"issue {i.get('id')} missing {k}")


def main():
    files = []
    for f in sorted((ROOT / "interpretive-drift-study" / "corpus").glob("case*.json")):
        files.append((f, check_drift))
    for f in sorted((ROOT / "ip-assignment-study" / "corpus").glob("case*.json")):
        files.append((f, check_ip))
    files.append((ROOT / "kestrel-injection-study" / "corpus" / "issues.json", check_kestrel))
    for f, fn in files:
        try:
            c = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            err(f, f"invalid JSON: {e}"); continue
        fn(f, c)
        status = c.get("_meta", {}).get("status", "")
        if "DRAFT" in status.upper():
            warn(f, "marked DRAFT: needs legal review before results are reported")
    for line in warns + errors:
        print(line)
    print(f"{len(files)} files checked: {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
