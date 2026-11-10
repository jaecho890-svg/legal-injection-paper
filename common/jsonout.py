"""
jsonout.py - pull a JSON value out of a model reply and check it against a small schema.

Models are asked to end with a JSON object. Replies sometimes wrap it in a ```json fence
or add prose around it, so extraction tries, in order: the last fenced block, the whole
reply, then the last balanced {...} or [...] in the text. Anything that still fails is
reported as a parse failure and counted in the analysis; it is never silently scored.
"""
import json
import re
from typing import Any, List, Optional, Tuple

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _last_top_level(text: str) -> Optional[Any]:
    """Scan left to right, decoding a JSON value wherever one starts; return the last top-level one."""
    dec = json.JSONDecoder()
    i, last = 0, None
    while i < len(text):
        if text[i] in "{[":
            try:
                obj, end = dec.raw_decode(text, i)
                last, i = obj, end
                continue
            except json.JSONDecodeError:
                pass
        i += 1
    return last


def extract(text: str) -> Tuple[Optional[Any], Optional[str]]:
    if not text or not text.strip():
        return None, "empty reply"
    fences = _FENCE.findall(text)
    for block in reversed(fences):
        try:
            return json.loads(block.strip()), None
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text.strip()), None
    except json.JSONDecodeError:
        pass
    cand = _last_top_level(text)
    if cand is not None:
        return cand, None
    return None, "no parseable JSON found"


# ---------- tiny schema checks ----------

def check(obj: Any, required: dict) -> List[str]:
    """required maps key -> one of: type, tuple of allowed values, or (min, max) int range as a list."""
    errs = []
    if not isinstance(obj, dict):
        return [f"expected object, got {type(obj).__name__}"]
    for k, rule in required.items():
        if k not in obj:
            errs.append(f"missing '{k}'")
            continue
        v = obj[k]
        if isinstance(rule, tuple):
            if v not in rule:
                errs.append(f"'{k}'={v!r} not in {rule}")
        elif isinstance(rule, list) and len(rule) == 2:
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not (rule[0] <= v <= rule[1]):
                errs.append(f"'{k}'={v!r} outside {rule}")
        elif isinstance(rule, type):
            if not isinstance(v, rule) or (rule is int and isinstance(v, bool)):
                errs.append(f"'{k}' should be {rule.__name__}")
    return errs
