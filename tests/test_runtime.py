import json
from pathlib import Path
import tempfile
import unittest

from stringos.runtime import AgentRuntime, PlanValidationError, ToolRegistry


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register("echo", lambda text: text)
        self.runtime = AgentRuntime(self.registry)

    def test_executes_registered_tool(self):
        report = self.runtime.execute_plan(
            [{"id": "echo", "tool": "echo", "args": {"text": "hello"}}]
        )
        self.assertTrue(report["completed"])
        self.assertEqual(report["results"]["echo"], "hello")

    def test_result_reference_passes_output_between_steps(self):
        report = self.runtime.execute_plan(
            [
                {"id": "first", "tool": "echo", "args": {"text": "hello"}},
                {"id": "second", "tool": "echo", "args": {"text": {"$ref": "first"}}},
            ]
        )
        self.assertEqual(report["results"]["second"], "hello")

    def test_retries_transient_failure(self):
        attempts = 0

        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError("temporary")
            return "recovered"

        self.registry.register("flaky", flaky)
        report = self.runtime.execute_plan(
            [{"id": "work", "tool": "flaky", "max_retries": 1}]
        )
        self.assertTrue(report["completed"])
        self.assertEqual([e["status"] for e in report["events"]], ["retry", "success"])

    def test_stops_after_retry_budget(self):
        def broken():
            raise RuntimeError("boom")

        self.registry.register("broken", broken)
        report = self.runtime.execute_plan(
            [{"id": "work", "tool": "broken", "max_retries": 1}]
        )
        self.assertFalse(report["completed"])
        self.assertEqual([e["status"] for e in report["events"]], ["retry", "failed"])

    def test_rejects_unknown_tool_before_execution(self):
        with self.assertRaises(PlanValidationError):
            self.runtime.execute_plan([{"tool": "does_not_exist"}])

    def test_rejects_invalid_retry_budget(self):
        with self.assertRaises(PlanValidationError):
            self.runtime.execute_plan([{"tool": "echo", "max_retries": 99}])

    def test_rejects_duplicate_ids_before_execution(self):
        calls = 0

        def counted(text):
            nonlocal calls
            calls += 1
            return text

        self.registry.register("counted", counted)
        with self.assertRaises(PlanValidationError):
            self.runtime.execute_plan(
                [
                    {"id": "same", "tool": "counted", "args": {"text": "first"}},
                    {"id": "same", "tool": "counted", "args": {"text": "second"}},
                ]
            )
        self.assertEqual(calls, 0)

    def test_rejects_missing_reference_before_execution(self):
        calls = 0

        def counted(text):
            nonlocal calls
            calls += 1
            return text

        self.registry.register("counted", counted)
        with self.assertRaises(PlanValidationError):
            self.runtime.execute_plan(
                [
                    {"id": "first", "tool": "counted", "args": {"text": "hello"}},
                    {
                        "id": "second",
                        "tool": "echo",
                        "args": {"text": {"$ref": "missing"}},
                    },
                ]
            )
        self.assertEqual(calls, 0)

    def test_rejects_forward_reference_before_execution(self):
        with self.assertRaises(PlanValidationError):
            self.runtime.execute_plan(
                [
                    {
                        "id": "first",
                        "tool": "echo",
                        "args": {"text": {"$ref": "second"}},
                    },
                    {"id": "second", "tool": "echo", "args": {"text": "hello"}},
                ]
            )

    def test_writes_machine_readable_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.json"
            self.runtime.execute_plan(
                [{"id": "echo", "tool": "echo", "args": {"text": "hello"}}],
                trace_path=path,
            )
            trace = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(trace["completed"])
            self.assertEqual(trace["events"][0]["tool"], "echo")

    def test_sensitive_step_stops_until_approved(self):
        calls = 0

        def sensitive_write(text):
            nonlocal calls
            calls += 1
            return text

        self.registry.register("sensitive_write", sensitive_write)
        report = self.runtime.execute_plan(
            [
                {
                    "id": "write",
                    "tool": "sensitive_write",
                    "args": {"text": "send"},
                    "requires_approval": True,
                }
            ]
        )

        self.assertFalse(report["completed"])
        self.assertEqual(report["awaiting_approval"], "write")
        self.assertEqual(calls, 0)

    def test_sensitive_step_runs_after_approval(self):
        calls = []

        def sensitive_write(text):
            calls.append(text)
            return text

        self.registry.register("sensitive_write", sensitive_write)
        runtime = AgentRuntime(self.registry, approved_steps={"write"})
        report = runtime.execute_plan(
            [
                {
                    "id": "write",
                    "tool": "sensitive_write",
                    "args": {"text": "send"},
                    "requires_approval": True,
                }
            ]
        )

        self.assertTrue(report["completed"])
        self.assertEqual(report["results"]["write"], "send")
        self.assertEqual(calls, ["send"])

    def test_checkpoint_prevents_duplicate_idempotent_step_on_replay(self):
        calls = []

        def enqueue(lead_id):
            calls.append(lead_id)
            return {"queued": lead_id}

        self.registry.register("enqueue", enqueue)
        plan = [
            {
                "id": "followup",
                "tool": "enqueue",
                "args": {"lead_id": "L-400"},
                "idempotency_key": "followup:L-400",
            }
        ]
        self.runtime.execute_plan(plan)
        resumed = AgentRuntime.from_checkpoint(
            self.registry,
            self.runtime.export_checkpoint(),
        )
        replay = resumed.execute_plan(plan)

        self.assertTrue(replay["completed"])
        self.assertEqual(replay["results"]["followup"], {"queued": "L-400"})
        self.assertEqual(calls, ["L-400"])

    def test_trace_records_failure_class(self):
        def temporary_failure():
            raise OSError("temporary")

        def permanent_failure():
            raise ValueError("bad request")

        self.registry.register("temporary_failure", temporary_failure)
        self.registry.register("permanent_failure", permanent_failure)
        transient_report = self.runtime.execute_plan(
            [{"id": "temporary", "tool": "temporary_failure", "max_retries": 0}]
        )
        report = self.runtime.execute_plan(
            [{"id": "permanent", "tool": "permanent_failure", "max_retries": 0}]
        )

        self.assertEqual(transient_report["events"][0]["failure_class"], "transient")
        self.assertEqual(report["events"][0]["failure_class"], "permanent")


if __name__ == "__main__":
    unittest.main()
