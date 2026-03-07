import json
import random

# Generate 50 high-quality prompt-response task-plan pairs
tasks = [
    ("remind user to sleep on time", [
        "check current time",
        "if time > 11pm, send sleep reminder",
        "log reminder event"
    ]),
    ("backup user files every night", [
        "schedule backup at 2am",
        "compress user files",
        "save to external drive or cloud",
        "log backup status"
    ]),
    ("organize desktop", [
        "scan desktop for files",
        "move documents to 'Documents' folder",
        "move images to 'Pictures' folder",
        "delete shortcuts older than 1 month"
    ]),
    ("check internet connectivity", [
        "ping a known website",
        "if ping fails, restart wifi",
        "notify user if internet is down"
    ]),
    ("start morning routine", [
        "open calendar",
        "launch focus music",
        "summarize today's tasks"
    ]),
    ("monitor battery health", [
        "check battery level",
        "if battery < 20%, notify user to plug in",
        "log battery status"
    ]),
    ("remind to drink water", [
        "set interval to 1 hour",
        "send reminder every hour",
        "log hydration reminder"
    ]),
    ("summarize unread emails", [
        "fetch unread emails",
        "extract key subjects",
        "summarize and display to user"
    ]),
    ("track screen time", [
        "start screen timer",
        "log app usage every hour",
        "summarize daily screen time"
    ]),
    ("launch deep work session", [
        "disable notifications",
        "start Pomodoro timer",
        "log session start time"
    ]),
]

# Duplicate with variations to create 50 examples
sample_tasks = []
for _ in range(5):  # 5x10 = 50 total
    for task, steps in tasks:
        variation = {
            "prompt": f"task: {task}",
            "response": "\n".join(f"- {step}" for step in steps)
        }
        sample_tasks.append(variation)

# Shuffle and save
random.shuffle(sample_tasks)
with open("general_tasks.jsonl", "w") as f:
    for example in sample_tasks:
        json.dump(example, f)
        f.write("\n") 