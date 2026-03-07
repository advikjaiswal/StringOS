import os
import shutil
import psutil  # for monitoring CPU etc.
from datetime import datetime

DOWNLOADS_FOLDER = os.path.expanduser("~/Downloads")

def clean_downloads():
    deleted = []
    for filename in os.listdir(DOWNLOADS_FOLDER):
        file_path = os.path.join(DOWNLOADS_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted.append(filename)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    return f"Deleted {len(deleted)} files: {', '.join(deleted)}"

def monitor_cpu_usage():
    usage = psutil.cpu_percent(interval=1)
    return f"CPU usage: {usage}%"

# You can add more task handlers here...
TASK_MAP = {
    "clean downloads": clean_downloads,
    "monitor CPU usage": monitor_cpu_usage
}

def run_task(task_prompt: str) -> str:
    for key in TASK_MAP:
        if key in task_prompt:
            return TASK_MAP[key]()
    return f"⚠️ No executable function found for: {task_prompt}" 