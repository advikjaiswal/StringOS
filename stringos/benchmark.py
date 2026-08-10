from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from statistics import mean
from typing import Any

from .runtime import AgentRuntime, PlanValidationError, ToolRegistry


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


def render_markdown(report: dict[str, Any]) -> str:
    config = report["configuration"]
    rows = [
        "# StringOS Reliability Benchmark",
        "",
        (
            f"Deterministic evaluation over {config['trials']} trials with a "
            f"{config['failure_probability_per_attempt']:.0%} transient failure "
            f"probability per attempt and seed {config['seed']}."
        ),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark StringOS failure recovery")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--failure-probability", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", type=Path, default=Path(".stringos_benchmark"))
    args = parser.parse_args()

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
    print(markdown)
    print(f"JSON report: {json_path}")


if __name__ == "__main__":
    main()
