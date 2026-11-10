"""
annotate.py - blinded human validation of the automated judge.

export: write a spreadsheet of judged items with the condition and model hidden and the
        rows shuffled, plus a separate key file. A human coder (ideally a lawyer) fills
        in human_label without seeing the judge's label or the condition.
kappa:  read the filled sheet back and report agreement with the judge (Cohen's kappa
        and raw agreement, per field and overall) plus a confusion table.

Usage after a study's `export-annotation` command has written the files:
  python3 -m common.annotate kappa --sheet <sheet.csv> --key <key.json>
"""
import argparse
import csv
import json
import pathlib
import random
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from . import stats


def export(items: List[dict], sheet: pathlib.Path, key: pathlib.Path, n: int, seed: int = 7) -> None:
    """items: dicts with key, field, options, text, auto_label. Sampling is stratified by
    (field, auto_label) so rare labels such as ACCEPT are represented."""
    rng = random.Random(seed)
    strata = defaultdict(list)
    for it in items:
        strata[(it["field"], it["auto_label"])].append(it)
    for v in strata.values():
        rng.shuffle(v)
    chosen, order = [], sorted(strata)
    while len(chosen) < min(n, len(items)):
        progressed = False
        for s in order:
            if strata[s] and len(chosen) < n:
                chosen.append(strata[s].pop()); progressed = True
        if not progressed:
            break
    rng.shuffle(chosen)
    sheet.parent.mkdir(parents=True, exist_ok=True)
    keymap = {}
    with sheet.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["blind_id", "field", "allowed_labels", "question", "text", "human_label", "notes"])
        for i, it in enumerate(chosen, 1):
            bid = f"A{i:04d}"
            w.writerow([bid, it["field"], " | ".join(it["options"]), it.get("question", ""), it["text"], "", ""])
            keymap[bid] = {"key": it["key"], "field": it["field"], "auto_label": it["auto_label"]}
    key.write_text(json.dumps(keymap, indent=2))
    print(f"wrote {len(chosen)} rows to {sheet} (key: {key}). Keep the key file away from the coder.")


def kappa(sheet: pathlib.Path, key: pathlib.Path, labels: Optional[Dict[str, str]] = None) -> str:
    """Human vs the judge whose labels are in the key; or, with `labels` (item key -> label), human vs
    another judge, counting only items that judge coded."""
    keymap = json.loads(key.read_text())
    by_field = defaultdict(lambda: ([], []))
    with sheet.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            h = row["human_label"].strip().upper()
            if not h:
                continue
            k = keymap[row["blind_id"]]
            judge = k["auto_label"] if labels is None else labels.get(k["key"])
            if judge is None:
                continue
            auto, hum = by_field[k["field"]]
            auto.append(str(judge).upper()); hum.append(h)
    lines = ["| field | n | agreement | Cohen's kappa |", "|---|---|---|---|"]
    all_a, all_h = [], []
    for f, (a, h) in sorted(by_field.items()):
        agree = sum(x == y for x, y in zip(a, h)) / len(a)
        lines.append(f"| {f} | {len(a)} | {agree:.2f} | {stats.cohen_kappa(a, h):.2f} |")
        all_a += a; all_h += h
    if all_a:
        agree = sum(x == y for x, y in zip(all_a, all_h)) / len(all_a)
        lines.append(f"| **all** | {len(all_a)} | {agree:.2f} | {stats.cohen_kappa(all_a, all_h):.2f} |")
        conf = Counter(zip(all_a, all_h))
        lines += ["", "Confusion (judge -> human):"] + [f"  {a} -> {h}: {c}" for (a, h), c in sorted(conf.items())]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kappa")
    k.add_argument("--sheet", required=True)
    k.add_argument("--key", required=True)
    args = ap.parse_args()
    print(kappa(pathlib.Path(args.sheet), pathlib.Path(args.key)))


if __name__ == "__main__":
    main()
