from __future__ import annotations

from pathlib import Path

from .runtime import AgentRuntime, ToolRegistry
from .tools import fail_once, read_text, summarize_text, write_text


def build_demo_runtime() -> AgentRuntime:
    registry = ToolRegistry()
    registry.register("read_text", read_text)
    registry.register("summarize_text", summarize_text)
    registry.register("write_text", fail_once(write_text))
    return AgentRuntime(registry)


def main() -> None:
    demo_dir = Path(".stringos_demo")
    demo_dir.mkdir(exist_ok=True)
    source = demo_dir / "input.txt"
    output = demo_dir / "summary.txt"
    trace = demo_dir / "trace.json"
    source.write_text(
        "Reliable agent systems need more than a planner. Tool calls can fail, "
        "arguments can be malformed, and operators need traces that explain what happened. "
        "StringOS separates planning from execution so those failures can be measured.",
        encoding="utf-8",
    )

    plan = [
        {"id": "read", "tool": "read_text", "args": {"path": str(source)}},
        {
            "id": "summary",
            "tool": "summarize_text",
            "args": {"text": {"$ref": "read"}, "max_chars": 150},
        },
        {
            "id": "write",
            "tool": "write_text",
            "args": {"path": str(output), "content": {"$ref": "summary"}},
            "max_retries": 1,
        },
    ]

    report = build_demo_runtime().execute_plan(plan, trace_path=trace)

    print("StringOS reliability demo")
    print("-------------------------")
    for event in report["events"]:
        marker = "OK" if event["status"] == "success" else "RETRY" if event["status"] == "retry" else "FAIL"
        detail = f" ({event['error']})" if event["error"] else ""
        print(
            f"{marker:5} {event['step_id']:<8} tool={event['tool']:<14} "
            f"attempt={event['attempt']} {event['duration_ms']:.3f}ms{detail}"
        )
    print(f"\ncompleted={report['completed']}")
    print(f"output={output}")
    print(f"trace={trace}")


if __name__ == "__main__":
    main()
