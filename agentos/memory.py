# memory.py
# Shared memory store for all agents with full recall support
from collections import defaultdict

class MemoryStore:
    def __init__(self):
        self.logs = defaultdict(list)  # logs[agent_name] = [(sender, message), ...]

    def remember(self, agent_name, sender, message):
        self.logs[agent_name].append((sender, message))

    def recall(self, agent_name, k=5):
        return self.logs[agent_name][-k:]  # last k messages

    def full_recall(self, agent_name):
        return self.logs[agent_name]  # all messages ever

    def clear(self, agent_name):
        self.logs[agent_name] = []

memory = MemoryStore()
