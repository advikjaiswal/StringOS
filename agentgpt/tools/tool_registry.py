# agentgpt/tools/tool_registry.py

class AgentToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, fn):
        self.tools[name] = fn

    def get(self, name):
        return self.tools.get(name)
