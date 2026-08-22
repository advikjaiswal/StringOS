from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from statistics import mean
from typing import Any, Callable

from .runtime import AgentRuntime, PlanValidationError, ToolRegistry


REAL_RUNTIME_MODULES = {
    "AgentRuntime": AgentRuntime,
    "ToolRegistry": ToolRegistry,
    "PlanValidationError": PlanValidationError,
}


@dataclass(frozen=True)
class PolicyResult:
    policy: str
    max_retries: int
    trials: int
    successful_tasks: int
    first_attempt_failures: int
    recovered_tasks: int
    task_success_rate: float
    recovery_rate: float
    average_attempts: float


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    plan: list[dict[str, Any]]
    recoverable_failure_injected: bool
    postcondition: Callable[[dict[str, Any], dict[str, Any]], bool]
    approved_steps: set[str] | None = None
    replay_from_checkpoint: bool = False


def _attempt_sequences(
    *, trials: int, failure_probability: float, attempts: int, seed: int
) -> list[list[bool]]:
    rng = random.Random(seed)
    return [
        [rng.random() < failure_probability for _ in range(attempts)]
        for _ in range(trials)
    ]


def _run_policy(sequences: list[list[bool]], max_retries: int) -> PolicyResult:
    successful_tasks = 0
    first_attempt_failures = 0
    recovered_tasks = 0
    attempts_per_task: list[int] = []

    for sequence in sequences:
        attempt_index = 0

        def injected_tool() -> str:
            nonlocal attempt_index
            should_fail = sequence[attempt_index]
            attempt_index += 1
            if should_fail:
                raise OSError("injected transient failure")
            return "ok"

        registry = ToolRegistry()
        registry.register("injected_tool", injected_tool)
        report = AgentRuntime(registry).execute_plan(
            [
                {
                    "id": "task",
                    "tool": "injected_tool",
                    "max_retries": max_retries,
                }
            ]
        )

        attempts_per_task.append(len(report["events"]))
        first_failed = report["events"][0]["status"] != "success"
        if first_failed:
            first_attempt_failures += 1
        if report["completed"]:
            successful_tasks += 1
            if first_failed:
                recovered_tasks += 1

    recovery_rate = (
        recovered_tasks / first_attempt_failures if first_attempt_failures else 1.0
    )
    return PolicyResult(
        policy=f"retry_budget_{max_retries}",
        max_retries=max_retries,
        trials=len(sequences),
        successful_tasks=successful_tasks,
        first_attempt_failures=first_attempt_failures,
        recovered_tasks=recovered_tasks,
        task_success_rate=round(successful_tasks / len(sequences), 4),
        recovery_rate=round(recovery_rate, 4),
        average_attempts=round(mean(attempts_per_task), 4),
    )


def _validation_detection_rate() -> dict[str, Any]:
    registry = ToolRegistry()
    registry.register("echo", lambda text="": text)
    runtime = AgentRuntime(registry)
    invalid_plans: list[Any] = [
        [],
        [{"tool": "unknown"}],
        [{"id": "same", "tool": "echo"}, {"id": "same", "tool": "echo"}],
        [
            {
                "id": "first",
                "tool": "echo",
                "args": {"text": {"$ref": "missing"}},
            }
        ],
    ]
    detected = 0
    for plan in invalid_plans:
        try:
            runtime.execute_plan(plan)
        except PlanValidationError:
            detected += 1
    return {
        "invalid_plans": len(invalid_plans),
        "detected_before_execution": detected,
        "detection_rate": round(detected / len(invalid_plans), 4),
    }


def _scenario_registry(side_effects: list[str]) -> ToolRegistry:
    registry = ToolRegistry()
    failure_counts: dict[str, int] = {}

    def echo(text: str = "") -> str:
        return text

    def timeout_once() -> str:
        failure_counts["timeout_once"] = failure_counts.get("timeout_once", 0) + 1
        if failure_counts["timeout_once"] == 1:
            raise TimeoutError("injected timeout")
        return "timeout recovered"

    def retryable_once() -> str:
        failure_counts["retryable_once"] = failure_counts.get("retryable_once", 0) + 1
        if failure_counts["retryable_once"] == 1:
            raise OSError("injected retryable failure")
        return "retryable recovered"

    def malformed_response() -> dict[str, str]:
        return {"unexpected": "shape"}

    def sensitive_write(record_id: str) -> dict[str, str]:
        side_effects.append(record_id)
        return {
            "record_id": record_id,
            "status": "written",
            "effect_receipt": f"receipt:{record_id}",
        }

    def partial_write(record_id: str) -> None:
        side_effects.append(record_id)
        raise OSError("injected partial side effect")

    def non_retryable() -> str:
        raise ValueError("injected permanent failure")

    registry.register("echo", echo)
    registry.register("timeout_once", timeout_once)
    registry.register("retryable_once", retryable_once)
    registry.register("malformed_response", malformed_response)
    registry.register_side_effect_tool("sensitive_write", sensitive_write)
    registry.register_side_effect_tool("partial_write", partial_write)
    registry.register("non_retryable", non_retryable)
    return registry


def _postcondition_result(report: dict[str, Any], spec: ScenarioSpec, side_effects: list[str]) -> tuple[bool, str]:
    if not report["completed"]:
        if report.get("manual_review_required"):
            return False, "outcome_unknown"
        if report.get("awaiting_approval"):
            return True, "approval_required"
        if report["events"] and report["events"][-1].get("failure_class") == "permanent":
            return True, "permanent_failure"
        return True, "runtime_failed"
    satisfied = spec.postcondition(report, {"side_effects": side_effects})
    return satisfied, "completed" if satisfied else "postcondition_failed"


def _expected_behaviour_correct(
    *,
    terminal_state: str,
    task_completed: bool,
    outcome_unknown: bool,
    manual_review_required: bool,
) -> bool:
    if outcome_unknown:
        return terminal_state == "outcome_unknown" and manual_review_required
    if task_completed:
        return True
    return terminal_state in {
        "approval_required",
        "permanent_failure",
        "postcondition_failed",
    }


def _scenario_specs() -> list[ScenarioSpec]:
    return [
        ScenarioSpec(
            name="normal_completion",
            plan=[{"id": "task", "tool": "echo", "args": {"text": "ok"}}],
            recoverable_failure_injected=False,
            postcondition=lambda report, _: report["results"].get("task") == "ok",
        ),
        ScenarioSpec(
            name="tool_timeout_recovery",
            plan=[{"id": "task", "tool": "timeout_once", "max_retries": 1}],
            recoverable_failure_injected=True,
            postcondition=lambda report, _: report["results"].get("task") == "timeout recovered",
        ),
        ScenarioSpec(
            name="retryable_tool_failure",
            plan=[{"id": "task", "tool": "retryable_once", "max_retries": 1}],
            recoverable_failure_injected=True,
            postcondition=lambda report, _: report["results"].get("task") == "retryable recovered",
        ),
        ScenarioSpec(
            name="malformed_tool_response",
            plan=[{"id": "task", "tool": "malformed_response"}],
            recoverable_failure_injected=False,
            postcondition=lambda report, _: report["results"].get("task", {}).get("status") == "ok",
        ),
        ScenarioSpec(
            name="permission_denial",
            plan=[{"id": "task", "tool": "sensitive_write", "args": {"record_id": "DENIED"}, "requires_approval": True}],
            recoverable_failure_injected=False,
            postcondition=lambda report, context: "DENIED" not in context["side_effects"],
        ),
        ScenarioSpec(
            name="partial_side_effect",
            plan=[{"id": "task", "tool": "partial_write", "args": {"record_id": "PARTIAL"}, "max_retries": 0}],
            recoverable_failure_injected=True,
            postcondition=lambda report, context: "PARTIAL" not in context["side_effects"],
        ),
        ScenarioSpec(
            name="false_success_trap",
            plan=[{"id": "task", "tool": "echo", "args": {"text": "claimed complete"}}],
            recoverable_failure_injected=False,
            postcondition=lambda report, _: report["results"].get("required_record") == "created",
        ),
        ScenarioSpec(
            name="non_retryable_failure",
            plan=[{"id": "task", "tool": "non_retryable", "max_retries": 0}],
            recoverable_failure_injected=False,
            postcondition=lambda report, _: not report["completed"],
        ),
        ScenarioSpec(
            name="duplicate_idempotency",
            plan=[{"id": "task", "tool": "sensitive_write", "args": {"record_id": "ONCE"}, "idempotency_key": "write:ONCE"}],
            recoverable_failure_injected=False,
            postcondition=lambda report, context: context["side_effects"].count("ONCE") == 1,
            replay_from_checkpoint=True,
        ),
    ]


def _run_scenario(spec: ScenarioSpec) -> dict[str, Any]:
    side_effects: list[str] = []
    registry = _scenario_registry(side_effects)
    runtime = AgentRuntime(registry, approved_steps=spec.approved_steps)
    report = runtime.execute_plan(spec.plan)
    events = list(report["events"])
    if spec.replay_from_checkpoint:
        replay_runtime = AgentRuntime.from_checkpoint(registry, runtime.export_checkpoint())
        replay_report = replay_runtime.execute_plan(spec.plan)
        report = replay_report
        events.extend(replay_report["events"])

    postcondition_satisfied, terminal_state = _postcondition_result(report, spec, side_effects)
    recovered = bool(
        spec.recoverable_failure_injected
        and report["completed"]
        and postcondition_satisfied
        and any(event["status"] == "retry" for event in events)
    )
    task_completed = bool(report["completed"] and postcondition_satisfied)
    outcome_unknown = bool(
        report.get("manual_review_required")
        or any(event.get("outcome") == "outcome_unknown" for event in events)
    )
    safe_rejection = terminal_state in {"approval_required", "permanent_failure"}
    expected_behaviour_correct = _expected_behaviour_correct(
        terminal_state=terminal_state,
        task_completed=task_completed,
        outcome_unknown=outcome_unknown,
        manual_review_required=bool(report.get("manual_review_required", False)),
    )
    return {
        "name": spec.name,
        "completed": task_completed,
        "task_completed": task_completed,
        "expected_behaviour_correct": expected_behaviour_correct,
        "safe_rejection": safe_rejection,
        "outcome_unknown": outcome_unknown,
        "manual_review_required": bool(report.get("manual_review_required", False)),
        "runtime_completed": report["completed"],
        "terminal_state": terminal_state,
        "recoverable_failure_injected": spec.recoverable_failure_injected,
        "recovered": recovered,
        "postcondition_satisfied": postcondition_satisfied,
        "side_effect_count": len(side_effects),
        "events": events,
    }


def run_scenario_benchmark() -> dict[str, Any]:
    scenarios = [_run_scenario(spec) for spec in _scenario_specs()]
    scenario_count = len(scenarios)
    recoverable = [row for row in scenarios if row["recoverable_failure_injected"]]
    recovered = [row for row in recoverable if row["recovered"]]
    completed = [row for row in scenarios if row["task_completed"]]
    correct = [row for row in scenarios if row["expected_behaviour_correct"]]
    safe_rejections = [row for row in scenarios if row["safe_rejection"]]
    unknown = [row for row in scenarios if row["outcome_unknown"]]
    return {
        "benchmark": "stringos_real_runtime_scenarios",
        "configuration": {
            "runtime_module": AgentRuntime.__module__,
            "real_stringos_runtime_exercised": AgentRuntime.__module__ == "stringos.runtime",
            "external_tools_mocked": True,
            "deterministic_failure_injection": True,
            "comparison_mode": "absolute_scenario_results",
            "baseline_toggle_available": False,
        },
        "metrics": {
            "scenario_count": scenario_count,
            "completed_tasks": len(completed),
            "successful_tasks": len(completed),
            "task_completion_rate": round(len(completed) / scenario_count, 4),
            "task_success_rate": round(len(completed) / scenario_count, 4),
            "correct_behaviour": len(correct),
            "expected_behaviour_correctness_rate": round(len(correct) / scenario_count, 4),
            "safe_rejections": len(safe_rejections),
            "safe_rejection_rate": round(len(safe_rejections) / scenario_count, 4),
            "recoverable_failures": len(recoverable),
            "recovered_tasks": len(recovered),
            "recovered_completion_rate": round(len(recovered) / len(recoverable), 4) if recoverable else 0.0,
            "recovery_rate": round(len(recovered) / len(recoverable), 4) if recoverable else 0.0,
            "uncontained_unknown_outcomes": len(unknown),
            "uncontained_unknown_outcome_rate": round(len(unknown) / scenario_count, 4),
            "postcondition_failures": sum(not row["postcondition_satisfied"] for row in scenarios),
            "side_effect_failures": sum(row["side_effect_count"] > 0 and not row["completed"] for row in scenarios),
        },
        "scenarios": scenarios,
    }


def run_benchmark(
    *, trials: int = 200, failure_probability: float = 0.35, seed: int = 7
) -> dict[str, Any]:
    if trials < 1:
        raise ValueError("trials must be at least 1")
    if not 0 <= failure_probability <= 1:
        raise ValueError("failure_probability must be between 0 and 1")

    retry_budgets = (0, 1, 2, 3)
    sequences = _attempt_sequences(
        trials=trials,
        failure_probability=failure_probability,
        attempts=max(retry_budgets) + 1,
        seed=seed,
    )
    results = [_run_policy(sequences, budget) for budget in retry_budgets]
    return {
        "benchmark": "transient_tool_failure_recovery",
        "configuration": {
            "trials": trials,
            "failure_probability_per_attempt": failure_probability,
            "seed": seed,
            "shared_failure_sequences": True,
        },
        "policies": [asdict(result) for result in results],
        "validation": _validation_detection_rate(),
    }


def run_multi_seed_benchmark(
    *, trials: int = 200, failure_probability: float = 0.35, seeds: list[int] | tuple[int, ...]
) -> dict[str, Any]:
    if not seeds:
        raise ValueError("seeds must contain at least one seed")

    reports = [
        run_benchmark(
            trials=trials,
            failure_probability=failure_probability,
            seed=seed,
        )
        for seed in seeds
    ]
    total_trials = trials * len(seeds)
    policies: list[dict[str, Any]] = []
    for policy_index, policy in enumerate(reports[0]["policies"]):
        successful_tasks = sum(
            report["policies"][policy_index]["successful_tasks"] for report in reports
        )
        first_attempt_failures = sum(
            report["policies"][policy_index]["first_attempt_failures"] for report in reports
        )
        recovered_tasks = sum(
            report["policies"][policy_index]["recovered_tasks"] for report in reports
        )
        per_seed_successful_tasks = {
            str(report["configuration"]["seed"]): report["policies"][policy_index]["successful_tasks"]
            for report in reports
        }
        recovery_rate = (
            recovered_tasks / first_attempt_failures if first_attempt_failures else 1.0
        )
        policies.append(
            {
                "policy": policy["policy"],
                "max_retries": policy["max_retries"],
                "trials": total_trials,
                "successful_tasks": successful_tasks,
                "first_attempt_failures": first_attempt_failures,
                "recovered_tasks": recovered_tasks,
                "task_success_rate": round(successful_tasks / total_trials, 4),
                "recovery_rate": round(recovery_rate, 4),
                "average_attempts": round(
                    mean(
                        report["policies"][policy_index]["average_attempts"]
                        for report in reports
                    ),
                    4,
                ),
                "per_seed_successful_tasks": per_seed_successful_tasks,
            }
        )

    return {
        "benchmark": "transient_tool_failure_recovery",
        "configuration": {
            "trials_per_seed": trials,
            "total_trials_per_policy": total_trials,
            "failure_probability_per_attempt": failure_probability,
            "seeds": list(seeds),
            "shared_failure_sequences": True,
        },
        "policies": policies,
        "validation": _validation_detection_rate(),
    }


def render_markdown(report: dict[str, Any]) -> str:
    config = report["configuration"]
    if "seeds" in config:
        description = (
            f"Deterministic evaluation over {config['total_trials_per_policy']} total "
            f"trials per policy ({config['trials_per_seed']} trials for each of "
            f"{len(config['seeds'])} seeds) with a "
            f"{config['failure_probability_per_attempt']:.0%} transient failure "
            f"probability per attempt and seeds {', '.join(map(str, config['seeds']))}."
        )
    else:
        description = (
            f"Deterministic evaluation over {config['trials']} trials with a "
            f"{config['failure_probability_per_attempt']:.0%} transient failure "
            f"probability per attempt and seed {config['seed']}."
        )
    rows = [
        "# StringOS Reliability Benchmark",
        "",
        description,
        "",
        "| Policy | Task success | Recovery after first failure | Average attempts |",
        "| --- | ---: | ---: | ---: |",
    ]
    for policy in report["policies"]:
        rows.append(
            f"| {policy['policy']} | {policy['task_success_rate']:.1%} | "
            f"{policy['recovery_rate']:.1%} | {policy['average_attempts']:.2f} |"
        )
    validation = report["validation"]
    rows.extend(
        [
            "",
            "## Plan validation",
            "",
            (
                f"Detected {validation['detected_before_execution']} of "
                f"{validation['invalid_plans']} invalid plans before tool execution "
                f"({validation['detection_rate']:.1%})."
            ),
            "",
            "This benchmark uses deterministic synthetic failures. It measures runtime "
            "behaviour, not language-model planning quality or production reliability.",
            "",
        ]
    )
    return "\n".join(rows)


def render_scenario_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    rows = [
        "# StringOS Real-Runtime Scenario Benchmark",
        "",
        "This benchmark imports and executes `stringos.runtime.AgentRuntime`. External tools are deterministic local test doubles; the core runtime, validation, approval, retry, idempotency and trace paths are real StringOS code.",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Scenarios | {metrics['scenario_count']} |",
        f"| Task completion rate | {metrics['task_completion_rate']:.1%} |",
        f"| Expected-behaviour correctness rate | {metrics['expected_behaviour_correctness_rate']:.1%} |",
        f"| Safe rejection rate | {metrics['safe_rejection_rate']:.1%} |",
        f"| Recovered completion rate | {metrics['recovered_completion_rate']:.1%} |",
        f"| Uncontained/unknown outcome rate | {metrics['uncontained_unknown_outcome_rate']:.1%} |",
        f"| Postcondition failures | {metrics['postcondition_failures']} |",
        f"| Side-effect failures | {metrics['side_effect_failures']} |",
        "",
        "| Scenario | Terminal state | Task completed | Correct behavior | Recovered | Side effects |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for scenario in report["scenarios"]:
        rows.append(
            f"| `{scenario['name']}` | `{scenario['terminal_state']}` | "
            f"{'yes' if scenario['task_completed'] else 'no'} | "
            f"{'yes' if scenario['expected_behaviour_correct'] else 'no'} | "
            f"{'yes' if scenario['recovered'] else 'no'} | "
            f"{scenario['side_effect_count']} |"
        )
    rows.extend([
        "",
        "No retry-policy baseline is reported for these scenarios because the current runtime does not expose a fair single toggle that disables only the reliability layer without changing the production execution path.",
        "",
    ])
    return "\n".join(rows)


def _write_scenario_csv(path: Path, scenarios: list[dict[str, Any]]) -> None:
    fields = [
        "name",
        "completed",
        "runtime_completed",
        "terminal_state",
        "task_completed",
        "expected_behaviour_correct",
        "safe_rejection",
        "outcome_unknown",
        "manual_review_required",
        "recoverable_failure_injected",
        "recovered",
        "postcondition_satisfied",
        "side_effect_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for scenario in scenarios:
            writer.writerow({field: scenario[field] for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark StringOS failure recovery")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--failure-probability", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--seeds", type=int, nargs="+")
    parser.add_argument("--output-dir", type=Path, default=Path(".stringos_benchmark"))
    args = parser.parse_args()

    if args.seeds:
        report = run_multi_seed_benchmark(
            trials=args.trials,
            failure_probability=args.failure_probability,
            seeds=args.seeds,
        )
    else:
        report = run_benchmark(
            trials=args.trials,
            failure_probability=args.failure_probability,
            seed=args.seed,
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "results.json"
    markdown_path = args.output_dir / "results.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = render_markdown(report)
    markdown_path.write_text(markdown, encoding="utf-8")
    scenario_report = run_scenario_benchmark()
    scenario_json_path = args.output_dir / "scenario_results.json"
    scenario_markdown_path = args.output_dir / "scenario_results.md"
    scenario_csv_path = args.output_dir / "scenario_results.csv"
    scenario_json_path.write_text(json.dumps(scenario_report, indent=2), encoding="utf-8")
    scenario_markdown = render_scenario_markdown(scenario_report)
    scenario_markdown_path.write_text(scenario_markdown, encoding="utf-8")
    _write_scenario_csv(scenario_csv_path, scenario_report["scenarios"])
    print(markdown)
    print()
    print(scenario_markdown)
    print(f"JSON report: {json_path}")
    print(f"Scenario JSON report: {scenario_json_path}")


if __name__ == "__main__":
    main()
