# start.py

import asyncio
from kernel import AgentKernel
from agent import PlannerAgent
from tool_agent import ToolUseAgent
from tools import web_scraper, file_writer, email_sender, summarizer, bash_runner
from memory import memory

# Add a simple receive method to agents if not present
class PlannerAgentWithReceive(PlannerAgent):
    async def receive(self, msg):
        await self.handle(msg)

class ToolUseAgentWithReceive(ToolUseAgent):
    async def receive(self, msg):
        await self.handle(msg)

# 1. Init kernel
kernel = AgentKernel()

# 2. Register agents
kernel.register_agent("Planner", PlannerAgentWithReceive("Planner", "Plan tasks"))
kernel.register_agent("ToolUseAgent", ToolUseAgentWithReceive("ToolUseAgent", "Use tools"))

# 3. Register tools
kernel.register_tool('web_scraper', web_scraper)
kernel.register_tool('file_writer', file_writer)
kernel.register_tool('email_sender', email_sender)
kernel.register_tool('summarizer', summarizer)
kernel.register_tool('bash_runner', bash_runner)

# 4. Auto-Recall Logs (Boot memory)
for agent_name in kernel.agents:
    logs = memory.recall(agent_name)
    if logs:
        print(f"[MEMORY] Restored {agent_name}'s last messages:")
        for sender, msg in logs:
            print(f"  - {sender}: {msg}")

# 5. User input loop
async def user_input_loop():
    while True:
        task = input("🧠 Give a task ('exit' to quit): ")
        if task.strip().lower() == "exit":
            break
        await kernel.send("Planner", {"from": "USER", "body": task})

# 6. Run everything
async def main():
    await asyncio.gather(
        kernel.run(),
        user_input_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
