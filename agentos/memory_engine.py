# agentgpt/memory/memory_engine.py

import json
import os
from datetime import datetime
import uuid

MEMORY_FILE = "agent_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def create_agent(agent_id=None, name=None, mission=None, parent=None):
    if agent_id is None:
        agent_id = f"agent_{str(uuid.uuid4())[:8]}"
    memory = load_memory()
    memory[agent_id] = {
        "id": agent_id,
        "name": name,
        "parent": parent,
        "mission": mission,
        "status": "active",
        "tools_used": [],
        "logs": [],
        "failures": [],
        "children": [],
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat()
    }
    save_memory(memory)
    return agent_id

def log_event(agent_id, event):
    memory = load_memory()
    agent = memory.get(agent_id)
    if agent:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event
        }
        agent["logs"].append(log_entry)
        agent["last_updated"] = datetime.utcnow().isoformat()
        save_memory(memory)
    else:
        print(f"Agent {agent_id} not found.")

def update_agent_memory(agent_id, key, value):
    memory = load_memory()
    agent = memory.get(agent_id)
    if agent:
        agent[key] = value
        agent["last_updated"] = datetime.utcnow().isoformat()
        save_memory(memory)
    else:
        print(f"Agent {agent_id} not found.")

def append_to_memory_list(agent_id, key, item):
    memory = load_memory()
    agent = memory.get(agent_id)
    if agent:
        agent[key].append(item)
        agent["last_updated"] = datetime.utcnow().isoformat()
        save_memory(memory)
    else:
        print(f"Agent {agent_id} not found.")

def clear_all_memories():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
