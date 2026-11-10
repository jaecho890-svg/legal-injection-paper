"""
mock.py - offline stand-in for a model, used only to test the harness end to end.

The mock does NOT simulate how real models behave. The experiment code passes it a
`mock_hint` describing the condition (for example how hard an arm pushes), and the mock
produces well-formed replies whose numbers move with that hint plus seeded noise. That
lets the run -> judge -> analysis chain be checked for plumbing errors before any money
is spent. Never report mock output as a result.
"""
import hashlib
import json
import random
import re

_MARK = re.compile(r"\[\[mock:push=([0-9.\-]+)\]\]")


def _rng(*parts) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def _out(text: str, spec: dict) -> dict:
    return {"text": text, "returned_model": spec["model"], "response_id": "mock",
            "stop_reason": "end_turn", "usage": {"input_tokens": 0, "output_tokens": len(text) // 4}}


def respond(spec, system, messages, params, hint):
    hint = hint or {}
    kind = hint.get("kind", "prose")
    sus = float(spec.get("susceptibility", 0.2))
    push = float(hint.get("push", 0.0)) * sus
    turn = sum(1 for m in messages if m["role"] == "user")
    rng = _rng(spec["alias"], system, messages[0]["content"], messages[-1]["content"], turn, hint.get("rep", 0))
    last_user = messages[-1]["content"]

    if kind == "prose":
        return _out(f"Mock analysis (sample {rng.random():.6f}).\n[[mock:push={push:.3f}]]", spec)

    if kind == "kestrel_judge":
        m = _MARK.search(last_user)
        p = float(m.group(1)) if m else 0.0
        labels = []
        for iid in hint["issue_ids"]:
            r = rng.random()
            lab = "ACCEPT" if r < p * 0.5 else "PARTIAL" if r < p else "NOT_ADDRESSED" if r > 0.98 else "PUSHBACK"
            labels.append({"issue_id": iid, "position": lab, "evidence": "mock quote"})
        return _out(json.dumps({"issues": labels, "adopts_framing": rng.random() < p,
                                "adopts_framing_evidence": "", "names_manipulation": rng.random() < 0.5}), spec)

    if kind == "seq_multi":
        kind = "seq_final" if last_user.startswith("All items have been provided") else "seq_step"

    if kind in ("seq_step", "seq_final"):
        # running estimate: baseline drifts toward hint target, push adds a persistent offset
        base = hint.get("baseline", 50)
        val = base + 25 * push + rng.gauss(0, 4)
        val = int(max(0, min(100, round(val))))
        obj = {"p": val, "conf": rng.choice(["LOW", "MED", "HIGH"]), "reason": "mock"}
        if kind == "seq_final":
            for k in hint.get("final_fields", []):
                obj[k] = "no" if k == "executed_deed_present" else "mock gap"
        return _out(json.dumps(obj), spec)

    if kind == "seq_single":
        n = hint["n_items"]
        base = hint.get("baseline", 50)
        steps = [{"step": k, "p": int(max(0, min(100, round(base + 25 * push + rng.gauss(0, 4))))),
                  "conf": "MED", "reason": "mock"} for k in range(1, n + 1)]
        final = dict(steps[-1]); final.pop("step")
        for k in hint.get("final_fields", []):
            final[k] = "no" if k == "executed_deed_present" else "mock gap"
        return _out(json.dumps({"steps": steps, "final": final}), spec)

    if kind == "dd_judge":
        m = _MARK.search(last_user)
        p = float(m.group(1)) if m else 0.0
        out = {}
        for key, labels in hint["fields"].items():
            good, bad = labels[0], labels[-1]
            out[key] = bad if rng.random() < p else good
        return _out(json.dumps(out), spec)

    return _out("mock", spec)
