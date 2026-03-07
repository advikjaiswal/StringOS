# agentgpt/executor/planner_executor.py
import traceback
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../agentos')))

from agentos.tool_executor import TOOL_MANAGER

class PlannerExecutor:
    def __init__(self, tool_registry=None, memory=None):
        # Keep tool_registry for backward compatibility, but use ToolManager
        self.tool_registry = tool_registry
        self.memory = memory  # Optional, plug in memory logger later

    def is_error_plan(self, plan):
        return (
            isinstance(plan, list)
            and len(plan) == 1
            and isinstance(plan[0], dict)
            and plan[0].get("tool") == "log_event"
        )

    def execute_plan(self, plan):
        # Bulletproof: abort if error plan
        if self.is_error_plan(plan):
            return
        # Patch: handle both dict and list
        if isinstance(plan, list):
            for subplan in plan:
                if isinstance(subplan, dict):
                    self.execute_plan(subplan)
            return
        if not isinstance(plan, dict):
            return
        task = plan.get("task", "unknown task")

        command = plan.get("command")
        if not command:
            return

        # Get command arguments from plan
        command_args = {}
        if "args" in plan:
            command_args = plan["args"]
        elif "channel_name" in plan:
            command_args["channel_name"] = plan["channel_name"]
        elif "description" in plan:
            command_args["description"] = plan["description"]

        try:
            result = TOOL_MANAGER.execute_tool(command, command_args)
        except Exception as e:
            traceback.print_exc()
            return

        # Optional: store in memory
        if self.memory:
            self.memory.log_event("task_execution", {
                "task": task,
                "command": command,
                "result": str(result)
            })
