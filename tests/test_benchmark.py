import tempfile
from pathlib import Path
import unittest

from stringos.benchmark import (
    REAL_RUNTIME_MODULES,
    render_markdown,
    run_benchmark,
    run_multi_seed_benchmark,
    run_scenario_benchmark,
)
from stringos.runtime import AgentRuntime


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_is_deterministic(self):
        first = run_benchmark(trials=50, failure_probability=0.35, seed=11)
        second = run_benchmark(trials=50, failure_probability=0.35, seed=11)
        self.assertEqual(first, second)

    def test_retry_budget_cannot_reduce_success_for_shared_sequences(self):
        report = run_benchmark(trials=100, failure_probability=0.4, seed=3)
        success_rates = [policy["task_success_rate"] for policy in report["policies"]]
        self.assertEqual(success_rates, sorted(success_rates))

    def test_multi_seed_benchmark_aggregates_policy_counts(self):
        report = run_multi_seed_benchmark(
            trials=10,
            failure_probability=0.35,
            seeds=[11, 17],
        )

        self.assertEqual(report["configuration"]["seeds"], [11, 17])
        self.assertEqual(report["configuration"]["trials_per_seed"], 10)
        self.assertEqual(report["configuration"]["total_trials_per_policy"], 20)
        for policy in report["policies"]:
            self.assertEqual(policy["trials"], 20)
            self.assertEqual(
                policy["task_success_rate"],
                round(policy["successful_tasks"] / 20, 4),
            )
            self.assertIn("per_seed_successful_tasks", policy)

    def test_validation_cases_are_detected_before_execution(self):
        report = run_benchmark(trials=5)
        self.assertEqual(report["validation"]["detection_rate"], 1.0)

    def test_markdown_contains_metrics(self):
        report = run_benchmark(trials=5)
        markdown = render_markdown(report)
        self.assertIn("Task success", markdown)
        self.assertIn("Plan validation", markdown)

    def test_report_can_be_written(self):
        report = run_benchmark(trials=5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.md"
            path.write_text(render_markdown(report), encoding="utf-8")
            self.assertGreater(path.stat().st_size, 0)

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            run_benchmark(trials=0)
        with self.assertRaises(ValueError):
            run_benchmark(failure_probability=1.1)

    def test_scenario_benchmark_uses_real_runtime_module(self):
        report = run_scenario_benchmark()

        self.assertIs(REAL_RUNTIME_MODULES["AgentRuntime"], AgentRuntime)
        self.assertEqual(report["configuration"]["runtime_module"], "stringos.runtime")
        self.assertTrue(report["configuration"]["real_stringos_runtime_exercised"])
        self.assertGreaterEqual(report["metrics"]["scenario_count"], 8)

    def test_policy_denial_precedes_side_effect_in_scenario_benchmark(self):
        report = run_scenario_benchmark()
        scenario = next(row for row in report["scenarios"] if row["name"] == "permission_denial")

        self.assertFalse(scenario["completed"])
        self.assertEqual(scenario["terminal_state"], "approval_required")
        self.assertEqual(scenario["side_effect_count"], 0)
        self.assertEqual(scenario["events"][0]["attempt"], 0)

    def test_success_requires_postcondition_in_scenario_benchmark(self):
        report = run_scenario_benchmark()
        scenario = next(row for row in report["scenarios"] if row["name"] == "false_success_trap")

        self.assertFalse(scenario["completed"])
        self.assertEqual(scenario["terminal_state"], "postcondition_failed")
        self.assertFalse(scenario["postcondition_satisfied"])

    def test_retries_do_not_duplicate_idempotent_side_effects(self):
        report = run_scenario_benchmark()
        scenario = next(row for row in report["scenarios"] if row["name"] == "duplicate_idempotency")

        self.assertTrue(scenario["completed"])
        self.assertEqual(scenario["side_effect_count"], 1)
        self.assertEqual([event["status"] for event in scenario["events"]], ["success", "skipped"])

    def test_scenario_metrics_are_derived_from_real_traces(self):
        report = run_scenario_benchmark()
        scenarios = report["scenarios"]
        metrics = report["metrics"]

        self.assertEqual(metrics["scenario_count"], len(scenarios))
        self.assertEqual(metrics["completed_tasks"], sum(row["task_completed"] for row in scenarios))
        self.assertEqual(
            metrics["correct_behaviour"],
            sum(row["expected_behaviour_correct"] for row in scenarios),
        )
        self.assertEqual(
            metrics["recoverable_failures"],
            sum(row["recoverable_failure_injected"] for row in scenarios),
        )
        self.assertEqual(
            metrics["recovered_tasks"],
            sum(row["recovered"] for row in scenarios if row["recoverable_failure_injected"]),
        )
        self.assertTrue(all(row["events"] for row in scenarios))

    def test_safely_rejected_permission_denial_counts_as_correct_not_completed(self):
        report = run_scenario_benchmark()
        scenario = next(row for row in report["scenarios"] if row["name"] == "permission_denial")

        self.assertFalse(scenario["task_completed"])
        self.assertTrue(scenario["expected_behaviour_correct"])
        self.assertTrue(scenario["safe_rejection"])

    def test_unknown_side_effect_counts_as_correct_manual_review_and_uncontained(self):
        report = run_scenario_benchmark()
        scenario = next(row for row in report["scenarios"] if row["name"] == "partial_side_effect")

        self.assertFalse(scenario["task_completed"])
        self.assertTrue(scenario["expected_behaviour_correct"])
        self.assertTrue(scenario["outcome_unknown"])
        self.assertTrue(scenario["manual_review_required"])

    def test_scenario_markdown_separates_completion_from_correctness(self):
        from stringos.benchmark import render_scenario_markdown

        markdown = render_scenario_markdown(run_scenario_benchmark())

        self.assertIn("Task completion rate", markdown)
        self.assertIn("Expected-behaviour correctness rate", markdown)
        self.assertIn("Safe rejection rate", markdown)
        self.assertIn("Uncontained/unknown outcome rate", markdown)


if __name__ == "__main__":
    unittest.main()
