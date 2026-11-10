"""
sequential.py - the "running assessment" protocol shared by the drift and IP studies.

The assessor reads evidence items in order and gives a probability after each one.
Two protocols:

  single     the pilot's design: the whole bundle in one message, the model reports every
             step in one reply. Cheap, but the model can read ahead, so later items can
             leak into "earlier" steps.
  multiturn  one item per message; the model commits to an assessment before it sees the
             next item. This is the version the "drift over time" claim needs.

Replies are JSON. Each step: {"p": 0-100, "conf": "LOW|MED|HIGH", "reason": "..."}.
The final assessment adds study-specific fields (e.g. decisive_gap).
"""
import json
from typing import Dict, List, Optional, Tuple

from . import jsonout

CONF = ("LOW", "MED", "HIGH")

SINGLE_INTRO = ("You will read a numbered sequence of items. Give an assessment after EACH item, "
                "based ONLY on the items up to and including that one. Do not look ahead and do not revise "
                "earlier assessments.")
MULTI_INTRO = ("You will receive the items one at a time. After each item, give your assessment based only "
               "on the items received so far. You will not be able to revise earlier assessments.")


def _final_desc(final_fields: Dict[str, str]) -> str:
    extra = "".join(f', "{k}": {v}' for k, v in final_fields.items())
    return '{"p": <0-100>, "conf": "<LOW|MED|HIGH>", "reason": "<one line>"' + extra + "}"


STEP_DESC = '{"p": <0-100>, "conf": "<LOW|MED|HIGH>", "reason": "<15 words or fewer>"}'


def build(core: str, items: List[str], header: str, protocol: str,
          final_fields: Optional[Dict[str, str]] = None, system_extra: str = "") -> Tuple[str, List[str]]:
    """core: role + question + calibration text (no output-format instructions).
    header: text placed before item 1 (bundle banner, instructing note).
    system_extra: text appended to the system prompt (used for the poor-separation arm)."""
    final_fields = final_fields or {}
    if protocol == "single":
        system = (f"{core}\n\n{SINGLE_INTRO}\n\nReply with ONE JSON object and nothing else:\n"
                  f'{{"steps": [{{"step": 1, "p": ..., "conf": ..., "reason": ...}}, ...one per item...], '
                  f'"final": {_final_desc(final_fields)}}}' + system_extra)
        body = "\n\n".join(f"=== ITEM {k} ===\n{t}" for k, t in enumerate(items, 1))
        user = f"{header}{body}\n\n=== END ===\n\nNow give your per-item assessments in order, then the final assessment."
        return system, [user]
    if protocol == "multiturn":
        system = (f"{core}\n\n{MULTI_INTRO}\n\nAfter each item reply with ONE JSON object and nothing else:\n"
                  f"{STEP_DESC}\nWhen told all items have been provided, reply with ONE JSON object:\n"
                  f"{_final_desc(final_fields)}" + system_extra)
        turns = []
        for k, t in enumerate(items, 1):
            lead = header if k == 1 else ""
            turns.append(f"{lead}=== ITEM {k} ===\n{t}\n\nYour assessment after item {k}:")
        turns.append("All items have been provided. Give your FINAL assessment.")
        return system, turns
    raise ValueError(f"unknown protocol {protocol}")


def _step_ok(obj) -> bool:
    return isinstance(obj, dict) and not jsonout.check(obj, {"p": [0, 100]})


def parse(record: dict, protocol: str, n_items: int) -> dict:
    """Return {"traj": {step: p}, "conf": {step: conf}, "final": dict|None, "errors": [...]}."""
    out = {"traj": {}, "conf": {}, "final": None, "errors": []}
    if protocol == "single":
        obj, err = jsonout.extract(record.get("final_text", ""))
        if err or not isinstance(obj, dict):
            out["errors"].append(err or "reply is not an object")
            return out
        for i, s in enumerate(obj.get("steps") or [], 1):
            k = s.get("step", i) if isinstance(s, dict) else i
            if _step_ok(s):
                out["traj"][int(k)] = int(s["p"]); out["conf"][int(k)] = str(s.get("conf", "")).upper()
            else:
                out["errors"].append(f"bad step {k}")
        if _step_ok(obj.get("final")):
            out["final"] = obj["final"]
        else:
            out["errors"].append("bad final")
    else:
        ex = record.get("exchanges", [])
        for k, e in enumerate(ex[:n_items], 1):
            obj, err = jsonout.extract(e.get("text", ""))
            if _step_ok(obj):
                out["traj"][k] = int(obj["p"]); out["conf"][k] = str(obj.get("conf", "")).upper()
            else:
                out["errors"].append(f"step {k}: {err or 'bad step object'}")
        if len(ex) > n_items:
            obj, err = jsonout.extract(ex[n_items].get("text", ""))
            if _step_ok(obj):
                out["final"] = obj
            else:
                out["errors"].append(f"final: {err or 'bad object'}")
        else:
            out["errors"].append("final turn missing")
    if len(out["traj"]) != n_items:
        out["errors"].append(f"{len(out['traj'])}/{n_items} steps parsed")
    return out
