import json
import os
from datetime import datetime

PLANNER_MEMORY_FILE = "agentos/planner_memory.json"

def load_planner_memory():
    if not os.path.exists(PLANNER_MEMORY_FILE):
        return []
    with open(PLANNER_MEMORY_FILE, "r") as f:
        return json.load(f)

def save_planner_memory(memory):
    with open(PLANNER_MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def log_plan_entry(agent_id, mission, decision, notes=None):
    memory = load_planner_memory()
    memory.append({
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "mission": mission,
        "decision": decision,
        "notes": notes or "",
    })
    save_planner_memory(memory)
