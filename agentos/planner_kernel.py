# planner_kernel.py

import json
from datetime import datetime
import sys
import os
import difflib
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from agentgpt.inference.generate_general import generate_plan_for_task
from agentos.tools_general import (
    clean_downloads_weekly,
    backup_system_logs_weekly,
    archive_browser_history_on_startup,
    monitor_cpu_usage_daily,
    remind_about_weekly_tasks,
    backup_logs_weekly,
    delete_old_screenshots,
    archive_zoom_recordings,
)
from agentos.task_runner import run_task

MEMORY_PATH = "agentgpt/memory/planner_memory.json"

TASK_FUNCTIONS = {
    "clean downloads weekly": clean_downloads_weekly,
    "backup system logs weekly": backup_system_logs_weekly,
    "archive browser history on startup": archive_browser_history_on_startup,
    "monitor CPU usage daily": monitor_cpu_usage_daily,
    "remind about weekly tasks": remind_about_weekly_tasks,
    "auto backup logs every Sunday": backup_logs_weekly,
    "delete old screenshots": delete_old_screenshots,
    "archive zoom recordings": archive_zoom_recordings,
}

# ---------------------- Memory Access ----------------------
def retrieve_similar_task_plan(prompt, memory_path=MEMORY_PATH):
    try:
        with open(memory_path, "r") as f:
            memory = json.load(f)
    except FileNotFoundError:
        return None

    if prompt in memory:
        return memory[prompt]["plan"]

    # Fallback: match on verb or object
    for task in memory:
        if prompt.split()[1] in task:
            return memory[task]["plan"]

    return None

# ---------------------- Plan Extractor ----------------------
def extract_plan_from_output(output):
    lines = output.strip().splitlines()
    plan_lines = [line.strip("- ") for line in lines if line.strip().startswith("-")]
    return plan_lines

# ---------------------- Baby-Agent Spawner ----------------------
def recursively_plan(prompt, depth=0):
    indent = "  " * depth
    print(f"{indent}🔁 Planning for: {prompt}")

    plan = retrieve_similar_task_plan(prompt)

    if plan:
        print(f"{indent}🧠 Memory Hit! Using past plan.")
        return plan

    output = generate_plan_for_task(prompt)
    plan = extract_plan_from_output(output) if output else []

    print(f"{indent}🆕 Generated Plan:")
    for step in plan:
        print(f"{indent}➡️ {step}")

        if any(verb in step for verb in ["optimize", "organize", "analyze", "summarize"]):
            print(f"{indent}👶 Spawning baby-agent for: {step}")
            sub_plan = recursively_plan(f"task: {step}", depth + 1)
            print(f"{indent}📦 Sub-plan for '{step}':")
            for sub_step in sub_plan:
                print(f"{indent}- {sub_step}")

    save_plan_to_memory(prompt, plan)
    return plan

# ---------------------- Save Plan to Memory ----------------------
def save_plan_to_memory(prompt, plan, memory_path=MEMORY_PATH):
    try:
        with open(memory_path, "r") as f:
            memory = json.load(f)
    except FileNotFoundError:
        memory = {}

    memory[prompt] = {
        "plan": plan,
        "last_run": datetime.now().isoformat(),
        "executed_by": "planner_kernel"
    }

    with open(memory_path, "w") as f:
        json.dump(memory, f, indent=2)

# ---------------------- CLI Runner ----------------------
def normalize(text):
    return re.sub(r'[^\w\s]', '', text).strip().lower()

def fuzzy_match_task(completion, task_keys, threshold=0.3):
    """Return the best fuzzy match from task_keys or None."""
    normalized_completion = normalize(completion)
    normalized_keys = [normalize(k) for k in task_keys]
    matches = difflib.get_close_matches(normalized_completion, normalized_keys, n=1, cutoff=threshold)
    if matches:
        # Return the original key that matches the normalized one
        idx = normalized_keys.index(matches[0])
        return list(task_keys)[idx]
    return None

def extract_subgoals(plan_text):
    lines = plan_text.splitlines()
    return [line.replace("- subgoal:", "").strip() for line in lines if line.startswith("- subgoal:")]

def execute_task(task_prompt, depth=0, max_depth=3):
    if depth > max_depth:
        print("❌ Max recursion depth reached.")
        return

    print(f"🔁 Planning for: {task_prompt}")
    # Hardcoded fallback for organize workspace
    if "organize workspace" in task_prompt:
        completion = '''plan:
- subgoal: clean downloads weekly
- subgoal: delete old screenshots
- subgoal: archive zoom recordings
'''
        plan = None
    else:
        plan = generate_plan_for_task(task_prompt)
        completion = plan if isinstance(plan, str) else json.dumps(plan)

    # If plan is a dict with a command, execute it
    if isinstance(plan, dict) and "command" in plan:
        result = run_task(plan)
        print(f"🚀 Execution Result:\n{result}")
        # Optionally log_event("execution_result", result)
        return

    if "subgoal:" in (completion or ""):
        subgoals = extract_subgoals(completion)
        for sg in subgoals:
            print(f"\n🧵 Subgoal -> {sg}")
            execute_task(sg, depth=depth+1, max_depth=max_depth)
    else:
        # Try to execute as before
        mode = "live" if "mode: live" in task_prompt else "dryrun"
        task_key = task_prompt.replace("mode: live", "").strip()
        task_fn = TASK_FUNCTIONS.get(task_key.lower())
        if task_fn:
            result = task_fn(mode=mode)
            print(f"🚀 Execution Result:\n{result}")
        else:
            # fallback to semantic/fuzzy match
            print(f"🧠 Completion for fallback: {completion}")
            print("🧠 Available TASK_FUNCTIONS keys:", list(TASK_FUNCTIONS.keys()))
            print("🧠 Raw completion:", completion)
            print("🧠 Raw task_prompt:", task_prompt)
            print("🧠 Completion repr:", repr(completion))
            for key, fn in TASK_FUNCTIONS.items():
                if key in (completion or '').lower() or key in task_prompt.lower():
                    print(f"🧠 Matched fallback function: {key}")
                    result = fn(mode=mode)
                    print(f"🚀 Execution Result:\n{result}")
                    break
            else:
                match = fuzzy_match_task(completion or '', TASK_FUNCTIONS.keys())
                if match:
                    print(f"🧠 Fuzzy matched task: {match}")
                    result = TASK_FUNCTIONS[match](mode=mode)
                    print(f"🚀 Execution Result:\n{result}")
                else:
                    print("⚠️ No executable function matched.")
                    result = f"No matching task handler found for: {task_prompt}"

if __name__ == "__main__":
    user_prompt = input("Task Prompt: ").strip()
    execute_task(user_prompt)

