# kernel.py
# Updated to support memory-aware agents and task routing

import asyncio

class AgentKernel:
    def __init__(self):
        self.agents = {}
        self.tools = {}

    def register_agent(self, name, agent):
        self.agents[name] = agent

    def register_tool(self, name, func):
        self.tools[name] = func

    def get_tool(self, name):
        return self.tools.get(name)

    async def send(self, to, message):
        agent = self.agents.get(to)
        if agent:
            await agent.receive(message)

    async def remove_agent(self, name):
        if name in self.agents:
            del self.agents[name]

    async def run(self):
        while True:
            await asyncio.sleep(1)  # simple loop to keep system alive

if __name__ == "__main__":
    from tool_runner import run_tool
    result = run_tool("list_files", directory="/Users/advikjaiswal/Desktop")
    print(result)
