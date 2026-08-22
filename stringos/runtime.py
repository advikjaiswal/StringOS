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
    failure_class: str | None = None
    outcome: str | None = None
    idempotency_key: str | None = None
    effect_receipt: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    fn: Callable[..., Any]
    side_effecting: bool = False
    reconcile: Callable[..., Any] | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        if not name or not callable(fn):
            raise ValueError("Tools require a non-empty name and callable implementation")
        self._tools[name] = ToolSpec(fn=fn)

    def register_side_effect_tool(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        reconcile: Callable[..., Any] | None = None,
    ) -> None:
        if not name or not callable(fn):
            raise ValueError("Tools require a non-empty name and callable implementation")
        if reconcile is not None and not callable(reconcile):
            raise ValueError("Reconciliation handler must be callable")
        self._tools[name] = ToolSpec(fn=fn, side_effecting=True, reconcile=reconcile)

    def get(self, name: str) -> Callable[..., Any]:
        return self.get_spec(name).fn

    def get_spec(self, name: str) -> ToolSpec:
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

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        approved_steps: set[str] | None = None,
        idempotency_results: dict[str, Any] | None = None,
        side_effect_attempts: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.registry = registry
        self.approved_steps = approved_steps or set()
        self._idempotency_results = idempotency_results or {}
        self._side_effect_attempts = side_effect_attempts or {}

    @classmethod
    def from_checkpoint(
        cls,
        registry: ToolRegistry,
        checkpoint: dict[str, Any],
        *,
        approved_steps: set[str] | None = None,
    ) -> AgentRuntime:
        return cls(
            registry,
            approved_steps=approved_steps,
            idempotency_results=dict(checkpoint.get("idempotency_results", {})),
            side_effect_attempts=dict(checkpoint.get("side_effect_attempts", {})),
        )

    def export_checkpoint(self) -> dict[str, Any]:
        return {
            "idempotency_results": dict(self._idempotency_results),
            "side_effect_attempts": dict(self._side_effect_attempts),
        }

    @staticmethod
    def _effect_receipt(result: Any) -> str | None:
        if isinstance(result, dict):
            receipt = result.get("effect_receipt") or result.get("external_operation_id")
            return str(receipt) if receipt else None
        return None

    def _reconcile_side_effect(
        self,
        *,
        spec: ToolSpec,
        step_id: str,
        tool_name: str,
        idempotency_key: str,
        effect_receipt: str | None,
    ) -> ExecutionEvent | None:
        if spec.reconcile is None:
            return None
        start = time.perf_counter()
        result = spec.reconcile(idempotency_key=idempotency_key, effect_receipt=effect_receipt)
        duration_ms = (time.perf_counter() - start) * 1000
        outcome = result.get("outcome") if isinstance(result, dict) else None
        receipt = self._effect_receipt(result) or effect_receipt
        if outcome == "confirmed_success":
            self._idempotency_results[idempotency_key] = result
        return ExecutionEvent(
            step_id=step_id,
            tool=tool_name,
            status="reconciled",
            attempt=0,
            duration_ms=round(duration_ms, 3),
            result_preview=str(result)[:160],
            outcome=outcome if outcome in {"confirmed_success", "confirmed_failure"} else "outcome_unknown",
            idempotency_key=idempotency_key,
            effect_receipt=receipt,
        )

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
        if "requires_approval" in step and not isinstance(step["requires_approval"], bool):
            raise PlanValidationError(f"Step {index} requires_approval must be a boolean")
        if "idempotency_key" in step:
            key = step["idempotency_key"]
            if not isinstance(key, str) or not key:
                raise PlanValidationError(f"Step {index} idempotency_key must be a non-empty string")
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
        awaiting_approval: str | None = None
        manual_review_required = False

        for step, step_id in zip(validated, step_ids):
            tool_name = step["tool"]
            tool_spec = self.registry.get_spec(tool_name)
            tool = tool_spec.fn
            max_retries = step.get("max_retries", 0)
            args = self._resolve(step.get("args", {}), results)
            idempotency_key = step.get("idempotency_key")

            if step.get("requires_approval") and step_id not in self.approved_steps:
                completed = False
                awaiting_approval = step_id
                events.append(
                    ExecutionEvent(
                        step_id=step_id,
                        tool=tool_name,
                        status="approval_required",
                        attempt=0,
                        duration_ms=0.0,
                        outcome="confirmed_failure",
                    )
                )
                break

            if idempotency_key in self._idempotency_results:
                results[step_id] = self._idempotency_results[idempotency_key]
                events.append(
                    ExecutionEvent(
                        step_id=step_id,
                        tool=tool_name,
                        status="skipped",
                        attempt=0,
                        duration_ms=0.0,
                        result_preview=str(results[step_id])[:160],
                        outcome="confirmed_success",
                        idempotency_key=idempotency_key,
                        effect_receipt=self._effect_receipt(results[step_id]),
                    )
                )
                continue

            if tool_spec.side_effecting and idempotency_key is None:
                idempotency_key = f"{tool_name}:{step_id}:{json.dumps(args, sort_keys=True, default=str)}"
            if tool_spec.side_effecting:
                self._side_effect_attempts[idempotency_key] = {
                    "step_id": step_id,
                    "tool": tool_name,
                    "status": "attempt_started",
                    "args": args,
                }

            success = False
            last_error: Exception | None = None
            attempt_limit = 1 if tool_spec.side_effecting else max_retries + 1
            for attempt in range(1, attempt_limit + 1):
                start = time.perf_counter()
                try:
                    result = tool(**args)
                    duration_ms = (time.perf_counter() - start) * 1000
                    effect_receipt = self._effect_receipt(result)
                    if tool_spec.side_effecting and effect_receipt is None:
                        events.append(
                            ExecutionEvent(
                                step_id=step_id,
                                tool=tool_name,
                                status="unknown",
                                attempt=attempt,
                                duration_ms=round(duration_ms, 3),
                                result_preview=str(result)[:160],
                                outcome="outcome_unknown",
                                idempotency_key=idempotency_key,
                            )
                        )
                        manual_review_required = True
                        completed = False
                        break
                    results[step_id] = result
                    outcome = "confirmed_success"
                    if idempotency_key is not None:
                        self._idempotency_results[idempotency_key] = result
                    events.append(
                        ExecutionEvent(
                            step_id=step_id,
                            tool=tool_name,
                            status="success",
                            attempt=attempt,
                            duration_ms=round(duration_ms, 3),
                            result_preview=str(result)[:160],
                            outcome=outcome,
                            idempotency_key=idempotency_key,
                            effect_receipt=effect_receipt,
                        )
                    )
                    success = True
                    break
                except Exception as exc:  # Runtime boundary: record arbitrary tool failures.
                    last_error = exc
                    duration_ms = (time.perf_counter() - start) * 1000
                    outcome = None
                    status = "retry" if attempt <= max_retries else "failed"
                    effect_receipt = None
                    if tool_spec.side_effecting:
                        outcome = "outcome_unknown" if isinstance(exc, (TimeoutError, OSError)) else "confirmed_failure"
                        status = "unknown" if outcome == "outcome_unknown" else "failed"
                    events.append(
                        ExecutionEvent(
                            step_id=step_id,
                            tool=tool_name,
                            status=status,
                            attempt=attempt,
                            duration_ms=round(duration_ms, 3),
                            error=f"{type(exc).__name__}: {exc}",
                            failure_class=self._classify_failure(exc),
                            outcome=outcome,
                            idempotency_key=idempotency_key,
                            effect_receipt=effect_receipt,
                        )
                    )
                    if outcome == "outcome_unknown":
                        reconciliation = self._reconcile_side_effect(
                            spec=tool_spec,
                            step_id=step_id,
                            tool_name=tool_name,
                            idempotency_key=idempotency_key,
                            effect_receipt=effect_receipt,
                        )
                        if reconciliation is not None:
                            events.append(reconciliation)
                            if reconciliation.outcome == "confirmed_success":
                                results[step_id] = self._idempotency_results[idempotency_key]
                                success = True
                            else:
                                completed = False
                            break
                        manual_review_required = True
                        completed = False
                        break

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
        if awaiting_approval is not None:
            report["awaiting_approval"] = awaiting_approval
        if manual_review_required:
            report["manual_review_required"] = True
        if trace_path is not None:
            path = Path(trace_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return report

    @staticmethod
    def _classify_failure(exc: Exception) -> str:
        if isinstance(exc, (TimeoutError, OSError)):
            return "transient"
        if isinstance(exc, PermissionError):
            return "permission"
        return "permanent"
