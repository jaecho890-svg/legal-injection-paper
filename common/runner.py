"""
runner.py - execute experiment jobs against pinned models and keep a complete ledger.

A job is a plain dict:
  run_id     unique id (also the output file name)
  model      alias from models.json
  role       "reviewer" or "judge" (selects default sampling params)
  system     system prompt
  turns      list of user messages; one item = single call, several = a true multi-turn
             conversation where each later message is sent after the model's reply
  meta       free-form condition labels, copied into the record for analysis
  mock_hint  only read by the mock backend
  params     optional overrides for temperature / max_tokens / seed

Each finished job is written to <dir>/<run_id>.json with the full request (system,
every turn), every response, the model id requested and returned, sampling params,
token usage, latency, timestamps and a fingerprint of the harness code. Jobs whose
record already exists with status "ok" are skipped, so an interrupted run resumes.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import threading
from typing import Dict, Iterable, List, Optional

from . import backends

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY_PATH = pathlib.Path(__file__).resolve().parent / "models.json"
_print_lock = threading.Lock()


# ---------- registry ----------

def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def resolve(alias: str, registry: Optional[dict] = None, allow_unverified: bool = False) -> dict:
    reg = registry or load_registry()
    if alias not in reg["models"]:
        raise SystemExit(f"unknown model alias '{alias}'. Known: {', '.join(reg['models'])}")
    spec = dict(reg["models"][alias], alias=alias)
    if not spec.get("verified") and not allow_unverified:
        raise SystemExit(
            f"model '{alias}' is marked verified=false in common/models.json (id: {spec['model']}).\n"
            f"Confirm the exact model id with the provider, update the entry and set verified=true.")
    return spec


def default_params(role: str, registry: Optional[dict] = None) -> dict:
    reg = registry or load_registry()
    return dict(reg["defaults"][role])


# ---------- provenance ----------

def harness_fingerprint(study_dir: pathlib.Path) -> str:
    h = hashlib.sha256()
    files = sorted(list((ROOT / "common").glob("*.py")) + list((ROOT / "common").glob("*.json"))
                   + list((study_dir / "harness").glob("*.py")) + list((study_dir / "harness").glob("*.json"))
                   + list((study_dir / "corpus").rglob("*.json")))
    for f in files:
        h.update(str(f.relative_to(ROOT)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _atomic_write(path: pathlib.Path, obj: dict) -> None:
    # unique temp name per process and thread: two runners judging the same record at once
    # (2026-11-06: the nightly API job and the gpt2 queue) must not rename each other's temp file
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


# ---------- execution ----------

def _execute(job: dict, spec: dict, params: dict, fingerprint: str) -> dict:
    record = {"run_id": job["run_id"], "meta": job.get("meta", {}), "role": job.get("role", "reviewer"),
              "model_alias": spec["alias"], "provider": spec["provider"], "requested_model": spec["model"],
              "params": params, "harness_fingerprint": fingerprint, "started_at": _now(),
              "system": job["system"], "exchanges": [], "status": "running"}
    messages: List[dict] = []
    try:
        if spec["provider"] in ("claude_cli", "codex_cli"):
            from . import cli_backends
            outs = cli_backends.converse(spec, job["system"], job["turns"], params)
            for i, (turn, out) in enumerate(zip(job["turns"], outs)):
                record["exchanges"].append({"turn": i + 1, "user": turn, **out})
            record["params"] = {**params, "temperature": "provider default (CLI cannot set it)"}
        else:
            for i, turn in enumerate(job["turns"]):
                messages.append({"role": "user", "content": turn})
                out = backends.call(spec, job["system"], list(messages), params,
                                    mock_hint=job.get("mock_hint"))
                messages.append({"role": "assistant", "content": out["text"]})
                record["exchanges"].append({"turn": i + 1, "user": turn, **out})
        record["status"] = "ok"
        record["returned_model"] = record["exchanges"][-1].get("returned_model")
        record["final_text"] = record["exchanges"][-1]["text"]
    except backends.BackendError as e:
        from .cli_backends import UsageLimit, USAGE_LIMIT_RE
        if isinstance(e, UsageLimit) or USAGE_LIMIT_RE.search(str(e)):
            raise UsageLimit(str(e)) from None
        record["status"] = "error"
        record["error"] = str(e)
    record["finished_at"] = _now()
    return record


def parse_model_reps(spec: str) -> Dict[str, int]:
    """'fable-5.1=10,opus-5.5=15' -> {'fable-5.1': 10, 'opus-5.5': 15}"""
    out = {}
    for part in (spec or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = int(v)
    return out


def in_sample(run_id: str, fraction: float) -> bool:
    """Deterministic sample membership: the same run_id is always in or out for a given fraction."""
    h = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16)
    return h / 0xFFFFFFFF < fraction


def apply_run_filters(jobs: List[dict]) -> List[dict]:
    """Per-model replicate caps (--model-reps) and deterministic sampling (--sample), set via env by the CLI flags."""
    caps = parse_model_reps(os.environ.get("LIJ_MODEL_REPS", ""))
    frac = float(os.environ.get("LIJ_SAMPLE", "1") or 1)
    out = []
    for j in jobs:
        rep = j.get("meta", {}).get("rep")
        if rep is not None and j["model"] in caps and rep > caps[j["model"]]:
            continue
        # model-reps also caps pipeline stages whose model is not the job's own (e.g. a fable orchestrator)
        orch = j.get("meta", {}).get("orchestrator")
        if rep is not None and orch in caps and rep > caps[orch]:
            continue
        if frac < 1 and not in_sample(j.get("meta", {}).get("reviewer_run_id") or j.get("meta", {}).get("source_run_id")
                                      or j["run_id"], frac):
            continue
        out.append(j)
    if len(out) != len(jobs):
        print(f"filters (model-reps={caps or '-'}, sample={frac}): {len(jobs)} -> {len(out)} jobs")
    return out


def run_jobs(jobs: List[dict], outdir: pathlib.Path, study_dir: pathlib.Path, workers: int = 4,
             dry_run: bool = False, force: bool = False, allow_unverified: bool = False,
             max_calls: Optional[int] = None) -> Dict[str, int]:
    jobs = apply_run_filters(jobs)
    reg = load_registry()
    fingerprint = harness_fingerprint(study_dir)

    pending = []
    for job in jobs:
        path = outdir / f"{job['run_id']}.json"
        if path.exists() and not force:
            try:
                if json.loads(path.read_text()).get("status") == "ok":
                    continue
            except json.JSONDecodeError:
                pass
        pending.append(job)

    # replicate-major order: rep 1 of every model x condition, then rep 2, ... so that a run cut short by a
    # usage window still leaves balanced cells (stable sort keeps the study's own order within a replicate)
    pending.sort(key=lambda j: j.get("meta", {}).get("rep", 0))
    calls = sum(len(j["turns"]) for j in pending)
    by_model: Dict[str, List[int]] = {}
    for j in pending:
        approx_in = (len(j["system"]) + sum(len(t) for t in j["turns"])) // 4
        b = by_model.setdefault(j["model"], [0, 0])
        b[0] += len(j["turns"]); b[1] += approx_in
    print(f"{len(jobs)} jobs, {len(jobs) - len(pending)} already done, {len(pending)} to run ({calls} API calls)")
    for m, (n, toks) in sorted(by_model.items()):
        print(f"  {m:18s} {n:6d} calls  ~{toks:,} input tokens (excl. multi-turn history)")
    if dry_run:
        print("dry run: nothing sent")
        return {"pending": len(pending), "calls": calls}
    if max_calls is not None and calls > max_calls:
        raise SystemExit(f"refusing: {calls} calls exceeds --max-calls {max_calls}")

    specs = {a: resolve(a, reg, allow_unverified) for a in {j["model"] for j in pending}}
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / "_invocations.jsonl").open("a") as fh:
        fh.write(json.dumps({"at": _now(), "argv": sys.argv, "fingerprint": fingerprint,
                             "jobs": len(pending), "calls": calls,
                             "models": {a: s["model"] for a, s in specs.items()}}) + "\n")

    counts = {"ok": 0, "error": 0}
    limit_hit = threading.Event()
    limit_msg = []

    def work(job):
        if limit_hit.is_set():
            return None
        params = default_params(job.get("role", "reviewer"), reg)
        params.update(job.get("params", {}))
        try:
            rec = _execute(job, specs[job["model"]], params, fingerprint)
        except Exception as e:  # usage window exhausted: stop the batch, write nothing for this job
            from .cli_backends import UsageLimit
            if not isinstance(e, UsageLimit):
                raise
            if not limit_hit.is_set():
                limit_msg.append(str(e)); limit_hit.set()
            return None
        _atomic_write(outdir / f"{job['run_id']}.json", rec)
        with _print_lock:
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
            done = counts["ok"] + counts["error"]
            msg = rec.get("error", "")[:160]
            print(f"  [{done}/{len(pending)}] {rec['status']:5s} {job['run_id']} {msg}")
        return rec

    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(work, pending))
    print(f"done: {counts['ok']} ok, {counts['error']} errors")
    if limit_hit.is_set():
        print(f"USAGE LIMIT HIT: {limit_msg[0][:300]}")
        counts["usage_limit"] = limit_msg[0]
    return counts


def load_records(outdir: pathlib.Path, status: str = "ok") -> List[dict]:
    recs = []
    if not outdir.exists():
        return recs
    for f in sorted(outdir.glob("*.json")):
        r = json.loads(f.read_text())
        if status is None or r.get("status") == status:
            recs.append(r)
    return recs


# ---------- shared CLI ----------

def add_run_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--models", default="mock-robust,mock-susceptible",
                    help="comma-separated aliases from common/models.json")
    ap.add_argument("--reps", type=int, default=20, help="replicates per cell")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="count jobs and tokens, send nothing")
    ap.add_argument("--force", action="store_true", help="re-run jobs that already have a result")
    ap.add_argument("--max-calls", type=int, default=None, help="refuse to start if more calls than this")
    ap.add_argument("--allow-unverified", action="store_true")
    ap.add_argument("--out", default="results_v2", help="output folder inside the study")
    ap.add_argument("--model-reps", action=_EnvAction, env="LIJ_MODEL_REPS", default=None,
                    help="per-model replicate caps, e.g. fable-5.1=10 (jobs above the cap are skipped)")
    ap.add_argument("--sample", action=_EnvAction, env="LIJ_SAMPLE", default=None,
                    help="run only a deterministic fraction of jobs, e.g. 0.1 (used for a second judge)")


class _EnvAction(argparse.Action):
    """Store the flag's value in an environment variable so run_jobs sees it at every call site."""
    def __init__(self, *a, env=None, **k):
        self.env = env
        super().__init__(*a, **k)

    def __call__(self, parser, ns, value, option_string=None):
        os.environ[self.env] = str(value)
        setattr(ns, self.dest, value)


def split_models(s: str) -> List[str]:
    return [m.strip() for m in s.split(",") if m.strip()]
