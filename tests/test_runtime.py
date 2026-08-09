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


if __name__ == "__main__":
    unittest.main()
