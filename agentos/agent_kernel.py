# agentos/agent_kernel.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cleaned up imports for new AgentKernel implementation
from agentgpt.executor.planner_executor import PlannerExecutor
from agentgpt.tools.tool_registry import AgentToolRegistry
from agentos.local_model import generate_with_local_gpt
from agentos.memory.memory_manager import MemoryManager
import json
import atexit

class AgentKernel:
    def __init__(self):
        self.tool_registry = AgentToolRegistry()
        self.executor = PlannerExecutor(self.tool_registry)
        self.memory = MemoryManager()
        self.load_tools()

    def load_tools(self):
        from agentgpt.tools.youtube_tools import start_youtube_channel
        self.tool_registry.register("start_youtube_channel", start_youtube_channel)

    def execute_task(self, prompt):
        # Step 2: Use memory during planning
        context_memories = self.memory.get("short_term", limit=5)
        context_str = "\n".join([m["content"] for m in context_memories])
        full_prompt = f"""Previous context:\n{context_str}\n\nCurrent task:\n{prompt}\n\nPlan:\n"""
        plan_json = generate_with_local_gpt(full_prompt)
        try:
            plan = json.loads(plan_json)
        except Exception as e:
            return
        self.executor.execute_plan(plan)
        # Step 3: Log results to memory
        self.memory.add("short_term", str(plan), source="planner")

if __name__ == "__main__":
    kernel = AgentKernel()
    # Step 4: Load memory on boot
    kernel.memory.load_memory()
    # Register graceful shutdown
    atexit.register(kernel.memory.save_memory)
    kernel.execute_task("Extract keywords from the following paragraph and email me the results: ‘AgentOS is the future of autonomous task execution and AI-driven productivity.'")
