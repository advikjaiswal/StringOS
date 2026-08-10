import tempfile
from pathlib import Path
import unittest

from stringos.benchmark import render_markdown, run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_is_deterministic(self):
        first = run_benchmark(trials=50, failure_probability=0.35, seed=11)
        second = run_benchmark(trials=50, failure_probability=0.35, seed=11)
        self.assertEqual(first, second)

    def test_retry_budget_cannot_reduce_success_for_shared_sequences(self):
        report = run_benchmark(trials=100, failure_probability=0.4, seed=3)
        success_rates = [policy["task_success_rate"] for policy in report["policies"]]
        self.assertEqual(success_rates, sorted(success_rates))

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


if __name__ == "__main__":
    unittest.main()
