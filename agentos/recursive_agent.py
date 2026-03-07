# agentos/recursive_agent.py

from agentos.runtime import AgentRuntime

class Agent:
    def __init__(self, name, task, memory=None, depth=0):
        self.name = name
        self.task = task
        self.memory = memory or []
        self.depth = depth
        self.runtime = AgentRuntime()

    def run(self):
        indent = "  " * self.depth
        print(f"\n{indent}👾 Agent '{self.name}' starting task: {self.task}")
        
        plan = self.runtime.run(self.task)  # Uses GPT to generate a plan
        print(f"{indent}🧠 Plan generated:\n{plan}")

        if not plan or not isinstance(plan, str):
            print(f"{indent}❌ No plan generated. Executing task directly.")
            result = self._execute_task(self.task)
            self.memory.append(result)
            print(f"{indent}✅ Task completed: {result}")
            return [result]
        
        sub_tasks = self._extract_subtasks(plan)
        results = []
        if not sub_tasks:
            result = self._execute_task(self.task)
            self.memory.append(result)
            print(f"{indent}✅ Task completed: {result}")
            return [result]
        for sub in sub_tasks:
            print(f"{indent}🧠 Spawning sub-agent for subtask: {sub}")
            sub_agent = Agent(name=f"{self.name}_child", task=sub, memory=self.memory, depth=self.depth+1)
            results.extend(sub_agent.run())
        return results

    def _extract_subtasks(self, plan):
        if not plan or not isinstance(plan, str):
            return []
        lines = [line.strip() for line in plan.split('\n') if line.strip()]
        subtasks = [line for line in lines if line[0].isdigit() and "." in line]
        return subtasks

    def _execute_task(self, task):
        return f"Executed: {task}"  # Placeholder for real logic or eval
