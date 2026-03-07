import random

# Core verbs and task templates
verbs = ["clean", "backup", "monitor", "notify", "optimize", "archive", "remind", "track", "analyze", "organize"]
objects = ["temp files", "user photos", "CPU usage", "downloads", "system logs", "browser history", "weekly tasks", "battery health", "disk space", "meeting notes"]
times = ["daily", "weekly", "every 2 hours", "at night", "before shutdown", "every Monday", "monthly", "during idle time", "on startup", "when low on space"]

# Helper to generate a task and a simple plan
def generate_task_plan():
    verb = random.choice(verbs)
    obj = random.choice(objects)
    time = random.choice(times)
    
    task = f"task: {verb} {obj} {time}"
    
    plan_steps = [
        f"- Identify location of {obj}",
        f"- Schedule action to {verb} it {time}",
        f"- Log completion status"
    ]
    plan = "plan:\n" + "\n".join(plan_steps)
    return f"{task}\n{plan}\n"

# Generate 5000 tasks
generated_tasks = [generate_task_plan() for _ in range(5000)]

# Join all tasks into a single string
full_dataset_text = "".join(generated_tasks)

# Save temporarily to a text file
file_path = "data_general_dump.txt"
with open(file_path, "w") as f:
    f.write(full_dataset_text)

file_path  # Return path so you can download it directl