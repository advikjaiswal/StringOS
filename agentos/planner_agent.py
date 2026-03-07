# agentos/planner_agent.py

import json
from agentgpt.inference.generate_plan import generate_plan

class PlannerAgent:
    def __init__(self):
        pass

    def plan(self, mission_description: str):
        prompt = f"""You are a PlannerAgent.
Given the mission: "{mission_description}", output a list of tasks in the following JSON format:

[
  {{"type": "tool", "tool": "tool_name", "args": ["arg1", "arg2"]}},
  {{"type": "code", "code": "some_python_code()"}}
]

Mission: {mission_description}
Tasks:
"""
        response = generate_plan(prompt)
        try:
            return json.loads(response)
        except Exception as e:
            print("⚠️ Failed to parse GPT output:", e)
            return []
