"""
Offline tests for the shared harness. Run from the paper folder:
    python3 -m unittest discover -s tests -v

The backend tests start a local HTTP server that imitates the Anthropic and OpenAI
endpoints, so request shape, auth headers, parameter handling and retry-on-429 are
checked without any API key or network access.
"""
import http.server
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import backends, jsonout, runner, sequential, stats  # noqa: E402


class FakeAPI(http.server.BaseHTTPRequestHandler):
    seen = []
    fail_first = {"n": 0}

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        FakeAPI.seen.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        if FakeAPI.fail_first["n"] > 0:
            FakeAPI.fail_first["n"] -= 1
            self.send_response(429); self.send_header("retry-after", "0"); self.end_headers()
            self.wfile.write(b'{"error":"rate"}'); return
        if self.path.endswith("/v1/messages"):
            out = {"id": "msg_1", "model": body["model"] + "-20261101", "stop_reason": "end_turn",
                   "content": [{"type": "text", "text": "hello"}], "usage": {"input_tokens": 3, "output_tokens": 1}}
        else:
            out = {"id": "cc_1", "model": body["model"] + "-2026-11-01", "system_fingerprint": "fp",
                   "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}], "usage": {"total_tokens": 4}}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeAPI)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        os.environ["FAKE_KEY"] = "test-key-not-real"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        FakeAPI.seen.clear(); FakeAPI.fail_first["n"] = 0

    def test_anthropic_shape(self):
        spec = {"alias": "a", "provider": "anthropic", "model": "claude-x", "key_env": "FAKE_KEY", "base_url": self.base}
        msgs = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}, {"role": "user", "content": "q2"}]
        out = backends.call(spec, "SYS", msgs, {"temperature": 0.7, "max_tokens": 50})
        req = FakeAPI.seen[-1]
        self.assertEqual(req["path"], "/v1/messages")
        self.assertEqual(req["headers"]["x-api-key"], "test-key-not-real")
        self.assertEqual(req["body"]["system"], "SYS")
        self.assertEqual(req["body"]["messages"], msgs)
        self.assertEqual(req["body"]["temperature"], 0.7)
        self.assertEqual(out["returned_model"], "claude-x-20261101")
        self.assertEqual(out["text"], "hello")

    def test_openai_shape_and_no_temperature(self):
        spec = {"alias": "o", "provider": "openai_compat", "model": "gpt-x", "key_env": "FAKE_KEY", "base_url": self.base,
                "supports_temperature": False, "max_tokens_param": "max_completion_tokens"}
        out = backends.call(spec, "SYS", [{"role": "user", "content": "q"}], {"temperature": 1.0, "max_tokens": 9})
        body = FakeAPI.seen[-1]["body"]
        self.assertEqual(FakeAPI.seen[-1]["path"], "/chat/completions")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "SYS"})
        self.assertNotIn("temperature", body)
        self.assertEqual(body["max_completion_tokens"], 9)
        self.assertEqual(out["text"], "hi")

    def test_retry_on_429(self):
        FakeAPI.fail_first["n"] = 2
        spec = {"alias": "a", "provider": "anthropic", "model": "m", "key_env": "FAKE_KEY", "base_url": self.base}
        out = backends.call(spec, "", [{"role": "user", "content": "q"}], {"max_tokens": 5})
        self.assertEqual(out["text"], "hello")
        self.assertEqual(len(FakeAPI.seen), 3)

    def test_missing_key(self):
        spec = {"alias": "a", "provider": "anthropic", "model": "m", "key_env": "NOPE_NOT_SET", "base_url": self.base}
        with self.assertRaises(backends.BackendError):
            backends.call(spec, "", [{"role": "user", "content": "q"}], {"max_tokens": 5})

    def test_env_base_url_ignored(self):
        os.environ["ANTHROPIC_BASE_URL"] = "http://should-not-be-used.invalid"
        spec = {"alias": "a", "provider": "anthropic", "model": "m", "key_env": "FAKE_KEY", "base_url": self.base}
        out = backends.call(spec, "", [{"role": "user", "content": "q"}], {"max_tokens": 5})
        self.assertEqual(out["base_url"], self.base)


class RunnerTests(unittest.TestCase):
    def test_unverified_refused(self):
        reg = {"models": {"x": {"provider": "anthropic", "model": "REPLACE", "verified": False}}}
        with self.assertRaises(SystemExit):
            runner.resolve("x", reg)

    def test_usage_limit_stops_batch_and_writes_nothing(self):
        from common import cli_backends
        calls = []
        real = runner._execute

        def fake(job, spec, params, fp):
            calls.append(job["run_id"])
            if job["run_id"] == "j2":
                raise cli_backends.UsageLimit("claude error: You've hit your 5-hour limit · resets 9:20pm (Australia/Sydney)")
            return real(job, spec, params, fp)
        runner._execute = fake
        try:
            with tempfile.TemporaryDirectory() as d:
                out = pathlib.Path(d)
                jobs = [{"run_id": f"j{i}", "model": "mock-robust", "system": "s", "turns": ["a"],
                         "meta": {"rep": i}, "mock_hint": {"kind": "prose"}} for i in range(1, 6)]
                c = runner.run_jobs(jobs, out, ROOT / "kestrel-injection-study", workers=1)
                self.assertIn("usage_limit", c)
                self.assertTrue((out / "j1.json").exists())
                self.assertFalse((out / "j2.json").exists())
                self.assertEqual(calls, ["j1", "j2"])
        finally:
            runner._execute = real

    def test_usage_limit_detected_from_cli_message(self):
        from common import cli_backends
        def boom():
            raise backends.BackendError("claude error: You've hit your 5-hour limit · resets 9:20pm (Australia/Sydney)")
        with self.assertRaises(cli_backends.UsageLimit):
            cli_backends._retrying(boom)

    def test_resume_and_multiturn(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            job = {"run_id": "t1", "model": "mock-robust", "system": "s", "turns": ["a", "b", "c"],
                   "mock_hint": {"kind": "prose"}}
            runner.run_jobs([job], out, ROOT / "kestrel-injection-study", workers=1)
            rec = json.loads((out / "t1.json").read_text())
            self.assertEqual(rec["status"], "ok")
            self.assertEqual(len(rec["exchanges"]), 3)
            self.assertEqual(rec["params"]["temperature"], 1.0)
            c = runner.run_jobs([job], out, ROOT / "kestrel-injection-study", workers=1)
            self.assertEqual(c.get("pending", 0), 0) if "pending" in c else self.assertEqual(c["ok"], 0)


class ParseTests(unittest.TestCase):
    def test_extract_variants(self):
        self.assertEqual(jsonout.extract('```json\n{"a": 1}\n```')[0], {"a": 1})
        self.assertEqual(jsonout.extract('Advice...\n{"a": 2}')[0], {"a": 2})
        self.assertEqual(jsonout.extract('[Footnote] text {"a": {"b": "}"}} tail')[0], {"a": {"b": "}"}})
        self.assertIsNone(jsonout.extract("no json")[0])

    def test_check(self):
        self.assertEqual(jsonout.check({"p": 40, "c": "LOW"}, {"p": [0, 100], "c": ("LOW", "HIGH")}), [])
        self.assertTrue(jsonout.check({"p": 140}, {"p": [0, 100]}))
        self.assertTrue(jsonout.check({"p": True}, {"p": [0, 100]}))

    def test_sequential_multiturn_parse(self):
        rec = {"exchanges": [{"text": '{"p": 50, "conf": "MED", "reason": "x"}'},
                             {"text": 'Sure. {"p": 60, "conf": "LOW", "reason": "y"}'},
                             {"text": '{"p": 55, "conf": "MED", "reason": "z", "decisive_gap": "deed"}'}]}
        p = sequential.parse(rec, "multiturn", 2)
        self.assertEqual(p["traj"], {1: 50, 2: 60})
        self.assertEqual(p["final"]["p"], 55)
        self.assertEqual(p["errors"], [])

    def test_sequential_single_parse_flags_missing(self):
        rec = {"final_text": json.dumps({"steps": [{"step": 1, "p": 40}], "final": {"p": 30}})}
        p = sequential.parse(rec, "single", 2)
        self.assertIn("1/2 steps parsed", p["errors"])


class StatsTests(unittest.TestCase):
    def test_wilson_known(self):
        p, lo, hi = stats.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3); self.assertAlmostEqual(hi, 0.7634, places=3)

    def test_holm(self):
        adj = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adj["a"], 0.03); self.assertAlmostEqual(adj["c"], 0.06); self.assertAlmostEqual(adj["b"], 0.06)

    def test_perm_detects_difference(self):
        self.assertLess(stats.perm_test([10] * 10 + [11] * 10, [0] * 10 + [1] * 10, b=2000), 0.01)
        self.assertGreater(stats.perm_test([1, 2, 3, 4], [1, 2, 3, 4], b=2000), 0.5)

    def test_kappa(self):
        self.assertAlmostEqual(stats.cohen_kappa(list("AABB"), list("AABB")), 1.0)
        self.assertAlmostEqual(stats.cohen_kappa(list("AB"), list("BA")), -1.0)

    def test_diff_ci_contains_truth(self):
        m, lo, hi = stats.diff_ci([5, 6, 7, 5, 6, 7], [1, 2, 3, 1, 2, 3])
        self.assertAlmostEqual(m, 4.0); self.assertLess(lo, 4.0); self.assertGreater(hi, 4.0)


if __name__ == "__main__":
    unittest.main()
