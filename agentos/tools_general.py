import os
import shutil
import time
import psutil
import datetime
import subprocess
from pathlib import Path

DOWNLOADS = str(Path.home() / "Downloads")
BACKUP = str(Path.home() / "Backups")
ARCHIVE = str(Path.home() / "BrowserArchive")

def clean_downloads_weekly(mode="dryrun"):
    count = 0
    if mode == "live":
        for file in os.listdir(DOWNLOADS):
            path = os.path.join(DOWNLOADS, file)
            if os.path.isfile(path):
                os.remove(path)
                count += 1
        return f"Deleted {count} files from Downloads."
    else:
        files = [f for f in os.listdir(DOWNLOADS) if os.path.isfile(os.path.join(DOWNLOADS, f))]
        return f"[DRYRUN] Would delete {len(files)} files from Downloads: {', '.join(files)}"

def backup_system_logs_weekly(mode="dryrun"):
    os.makedirs(BACKUP, exist_ok=True)
    src = "/var/log/system.log"
    dst = os.path.join(BACKUP, f"system_backup_{int(time.time())}.log")
    if mode == "live":
        shutil.copy(src, dst)
        return f"Backed up system.log to {dst}"
    else:
        return f"[DRYRUN] Would back up {src} to {dst}"

def archive_browser_history_on_startup(mode="dryrun"):
    os.makedirs(ARCHIVE, exist_ok=True)
    chrome_path = str(Path.home() / "Library/Application Support/Google/Chrome/Default/History")
    if os.path.exists(chrome_path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(ARCHIVE, f"History_{timestamp}")
        if mode == "live":
            shutil.copy(chrome_path, dest)
            return f"Archived Chrome history to {dest}"
        else:
            return f"[DRYRUN] Would archive Chrome history to {dest}"
    return "Chrome history not found."

def monitor_cpu_usage_daily(mode="dryrun"):
    usage = psutil.cpu_percent(interval=1)
    log_path = os.path.join(BACKUP, "cpu_usage_log.txt")
    os.makedirs(BACKUP, exist_ok=True)
    if mode == "live":
        with open(log_path, "a") as f:
            f.write(f"{datetime.datetime.now()}: CPU usage = {usage}%\n")
        return f"Logged CPU usage: {usage}%"
    else:
        return f"[DRYRUN] Would log CPU usage: {usage}% to {log_path}"

def remind_about_weekly_tasks(mode="dryrun"):
    message = "Don't forget to complete your weekly tasks! 💼"
    if mode == "live":
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "AgentOS Reminder"'
        ])
        return "Reminder sent!"
    else:
        return f"[DRYRUN] Would send reminder: {message}"

def backup_logs_weekly(mode="dryrun"):
    source_path = "/var/log/system.log"
    backup_path = f"{BACKUP}/system_backup_{int(time.time())}.log"
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    if mode == "live":
        shutil.copy(source_path, backup_path)
        print(f"✅ Backed up {source_path} to {backup_path}")
        return f"Backed up logs to {backup_path}"
    else:
        print(f"[DRYRUN] Would back up {source_path} to {backup_path}")
        return f"[DRYRUN] Would back up logs to {backup_path}"

def delete_old_screenshots(mode="dryrun"):
    # Dummy implementation
    screenshots_dir = str(Path.home() / "Desktop")
    deleted = []
    for file in os.listdir(screenshots_dir):
        if file.startswith("Screenshot") and file.endswith(".png"):
            path = os.path.join(screenshots_dir, file)
            if mode == "live":
                os.remove(path)
                deleted.append(file)
            else:
                deleted.append(file)
    if mode == "live":
        return f"Deleted {len(deleted)} screenshots."
    else:
        return f"[DRYRUN] Would delete {len(deleted)} screenshots: {', '.join(deleted)}"

def archive_zoom_recordings(mode="dryrun"):
    # Dummy implementation
    zoom_dir = str(Path.home() / "Documents/Zoom")
    archive_dir = str(Path.home() / "ZoomArchive")
    if not os.path.exists(zoom_dir):
        return f"Zoom recordings directory not found: {zoom_dir}"
    os.makedirs(archive_dir, exist_ok=True)
    moved = []
    for file in os.listdir(zoom_dir):
        if file.endswith(".mp4"):
            src = os.path.join(zoom_dir, file)
            dst = os.path.join(archive_dir, file)
            if mode == "live":
                shutil.move(src, dst)
                moved.append(file)
            else:
                moved.append(file)
    if mode == "live":
        return f"Archived {len(moved)} Zoom recordings."
    else:
        return f"[DRYRUN] Would archive {len(moved)} Zoom recordings: {', '.join(moved)}"

# Add more task-function mappings here
TASK_TOOL_MAP = {
    "backup system logs weekly": backup_system_logs_weekly,
} 