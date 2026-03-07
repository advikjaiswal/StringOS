import os
import json
import time

class MemoryManager:
    def __init__(self):
        self.memory_file = os.path.join(os.path.dirname(__file__), "memory_store.json")
        self.memory = {
            "short_term": [],
            "long_term": [],
            "scratchpad": []
        }
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    self.memory = json.load(f)
            except json.JSONDecodeError:
                print("[MemoryManager] Warning: memory_store.json is corrupted. Reinitializing...")
                self.memory = {
                    "short_term": [],
                    "long_term": [],
                    "scratchpad": []
                }

    def save_memory(self):
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2)

    def add(self, memory_type, content, source="unknown", score=1.0):
        entry = {
            "timestamp": time.time(),
            "content": content,
            "source": source,
            "score": score
        }
        if memory_type not in self.memory:
            raise ValueError(f"Invalid memory type: {memory_type}")

        self.memory[memory_type].append(entry)
        self.save_memory()

    def get(self, memory_type, limit=10):
        if memory_type not in self.memory:
            raise ValueError(f"Invalid memory type: {memory_type}")

        return sorted(
            self.memory[memory_type], key=lambda x: -x.get("score", 0.0)
        )[:limit]

    def clear(self, memory_type=None):
        if memory_type:
            if memory_type not in self.memory:
                raise ValueError(f"Invalid memory type: {memory_type}")
            self.memory[memory_type] = []
        else:
            for k in self.memory:
                self.memory[k] = []
        self.save_memory()
