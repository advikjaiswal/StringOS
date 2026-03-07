# agent.py (Planner agent upgraded to use memory + custom GPT + spawning)
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import asyncio
from agent_core import Agent
from memory import memory
try:
    from agentos.local_model import generate_with_local_gpt
except ImportError as e:
    print(f"[WARN] Could not import local_model: {e}")
from tool_agent import ToolUseAgent

class PlannerAgent(Agent):
    async def handle(self, msg):
        sender = msg['from']
        body = msg['body']

        # 1. Store message in memory
        memory.remember(self.name, sender, body)

        # 2. Recall recent memory to build context for GPT
        history = memory.recall(self.name)
        formatted_log = '\n'.join([f"{s}: {m}" for s, m in history])
        prompt = f"""You are an autonomous Planner in an AI Operating System.

Your role is to analyze goals and create tasks for agents to complete.
Here is recent memory from your system:
{formatted_log}

Based on the last message: "{body}", generate tasks in JSON format like:
[
    {{
        "type": "tool",
        "tool": "web_scraper",
        "args": ["https://example.com"]
    }},
    {{
        "type": "code",
        "code": "2 + 2"
    }}
]
If no action needed, return [].
"""

        print("\n📝 Prompt sent to GPT:\n", prompt)
        try:
            response = generate_with_local_gpt(prompt)
            print("🧾 Raw GPT output:", response)
            tasks = json.loads(response)
        except Exception as e:
            print("🚨 GPT parsing failed:", e)
            tasks = [{"type": "say", "text": "Sorry, I didn't understand that."}]

        # 4. Spawn agents for each task
        for i, task in enumerate(tasks):
            agent_name = f"{self.name}_child_{i}"
            if task['type'] == 'tool':
                await self.kernel.spawn(agent_name, ToolUseAgent, self.name)
                await self.kernel.send(agent_name, {
                    'from': self.name,
                    'body': f"tool: {json.dumps(task)}"
                })
            elif task['type'] == 'code':
                await self.kernel.spawn(agent_name, ToolUseAgent, self.name)
                await self.kernel.send(agent_name, {
                    'from': self.name,
                    'body': f"code: {task['code']}"
                })
            elif task['type'] == 'say':
                print(f"[PlannerAgent] {task['text']}")
            else:
                await self.send('USER', f"⚠️ Unknown task type: {task['type']}")

        if not tasks:
            await self.send('USER', "🤖 No actionable tasks generated.")

    def plan(self, task_description: str):
        """Generate a plan for the given task using the local GPT model."""
        import json
        
        prompt = f"Plan a mission for: {task_description}"
        raw_plan = generate_with_local_gpt(prompt)
        
        try:
            plan = json.loads(raw_plan)
            return plan
        except json.JSONDecodeError:
            print("❌ Failed to parse plan from model output.")
            return [{"type": "say", "text": raw_plan}]  # fallback

# === Safe Executor Usage Example (Integrated) ===
if __name__ == "__main__":
    from agentos.executor import safe_execute
    # Simulate model output (could be replaced with real model call)
    model_output = '{"task": "delete the ss folder", "frequency": "one-time", "subtasks": ["Remove the ss folder and its contents"], "command": "delete_ss_folder"}'
    import json
    try:
        parsed_json = json.loads(model_output)
        print(f"[INFO] Parsed model output: {parsed_json}")
        if "command" in parsed_json:
            safe_execute(parsed_json["command"])
        else:
            print("[INFO] No command to execute in model output.")
    except Exception as e:
        print(f"[ERROR] Failed to parse model output: {e}")
