import os
import json

MEMORY_PATH = "agentgpt/memory/planner_mem.json"

def load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    return {}

def save_memory(mem):
    with open(MEMORY_PATH, "w") as f:
        json.dump(mem, f, indent=2)

def log_task(prompt, plan):
    memory = load_memory()
    memory[prompt] = plan
    save_memory(memory)

def retrieve_similar(prompt):
    memory = load_memory()
    return memory.get(prompt, None)
