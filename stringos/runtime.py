from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable


class PlanValidationError(ValueError):
    """Raised when a planner emits a plan that the runtime cannot execute safely."""


@dataclass
class ExecutionEvent:
    step_id: str
    tool: str
    status: str
    attempt: int
    duration_ms: float
    error: str | None = None
    result_preview: str | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        if not name or not callable(fn):
            raise ValueError("Tools require a non-empty name and callable implementation")
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise PlanValidationError(f"Unknown tool: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))


class AgentRuntime:
    """Execute a planner-produced tool plan with validation, retries, and traces.

    The runtime deliberately does not decide how a plan is generated. A local
    model, hosted model, human, or test fixture can all produce the same schema.
    This keeps planner quality separate from execution reliability.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    @staticmethod
    def _validate_step(step: Any, index: int) -> dict[str, Any]:
        if not isinstance(step, dict):
            raise PlanValidationError(f"Step {index} must be an object")
        if not isinstance(step.get("tool"), str) or not step["tool"]:
            raise PlanValidationError(f"Step {index} requires a non-empty 'tool'")
        if "args" in step and not isinstance(step["args"], dict):
            raise PlanValidationError(f"Step {index} 'args' must be an object")
        if "max_retries" in step:
            retries = step["max_retries"]
            if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0 or retries > 3:
                raise PlanValidationError(
                    f"Step {index} max_retries must be an integer between 0 and 3"
                )
        return step

    @staticmethod
    def _resolve(value: Any, results: dict[str, Any]) -> Any:
        if isinstance(value, dict) and set(value) == {"$ref"}:
            ref = value["$ref"]
            if ref not in results:
                raise PlanValidationError(f"Unknown result reference: {ref}")
            return results[ref]
        if isinstance(value, list):
            return [AgentRuntime._resolve(item, results) for item in value]
        if isinstance(value, dict):
            return {key: AgentRuntime._resolve(item, results) for key, item in value.items()}
        return value

    @staticmethod
    def _result_references(value: Any) -> set[str]:
        if isinstance(value, dict) and set(value) == {"$ref"}:
            ref = value["$ref"]
            if not isinstance(ref, str) or not ref:
                raise PlanValidationError("Result references must name a non-empty step id")
            return {ref}
        if isinstance(value, list):
            return set().union(
                *(AgentRuntime._result_references(item) for item in value), set()
            )
        if isinstance(value, dict):
            return set().union(
                *(AgentRuntime._result_references(item) for item in value.values()), set()
            )
        return set()

    def execute_plan(
        self,
        plan: Any,
        *,
        trace_path: str | Path | None = None,
        raise_on_failure: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(plan, list) or not plan:
            raise PlanValidationError("Plan must be a non-empty list of tool-call objects")

        validated = [self._validate_step(step, i) for i, step in enumerate(plan)]
        step_ids: list[str] = []
        prior_ids: set[str] = set()
        for index, step in enumerate(validated):
            raw_id = step.get("id")
            if raw_id is not None and (not isinstance(raw_id, str) or not raw_id):
                raise PlanValidationError(f"Step {index} 'id' must be a non-empty string")
            step_id = raw_id or f"step_{index + 1}"
            if step_id in prior_ids:
                raise PlanValidationError(f"Duplicate step id: {step_id}")

            references = self._result_references(step.get("args", {}))
            unavailable = references - prior_ids
            if unavailable:
                names = ", ".join(sorted(unavailable))
                raise PlanValidationError(
                    f"Step {index} references unavailable earlier result(s): {names}"
                )

            self.registry.get(step["tool"])
            step_ids.append(step_id)
            prior_ids.add(step_id)

        events: list[ExecutionEvent] = []
        results: dict[str, Any] = {}
        completed = True

        for step, step_id in zip(validated, step_ids):
            tool_name = step["tool"]
            tool = self.registry.get(tool_name)
            max_retries = step.get("max_retries", 0)
            args = self._resolve(step.get("args", {}), results)

            success = False
            last_error: Exception | None = None
            for attempt in range(1, max_retries + 2):
                start = time.perf_counter()
                try:
                    result = tool(**args)
                    duration_ms = (time.perf_counter() - start) * 1000
                    results[step_id] = result
                    events.append(
                        ExecutionEvent(
                            step_id=step_id,
                            tool=tool_name,
                            status="success",
                            attempt=attempt,
                            duration_ms=round(duration_ms, 3),
                            result_preview=str(result)[:160],
                        )
                    )
                    success = True
                    break
                except Exception as exc:  # Runtime boundary: record arbitrary tool failures.
                    last_error = exc
                    duration_ms = (time.perf_counter() - start) * 1000
                    events.append(
                        ExecutionEvent(
                            step_id=step_id,
                            tool=tool_name,
                            status="retry" if attempt <= max_retries else "failed",
                            attempt=attempt,
                            duration_ms=round(duration_ms, 3),
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )

            if not success:
                completed = False
                if raise_on_failure and last_error is not None:
                    raise last_error
                break

        report = {
            "completed": completed,
            "results": results,
            "events": [asdict(event) for event in events],
        }
        if trace_path is not None:
            path = Path(trace_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return report
