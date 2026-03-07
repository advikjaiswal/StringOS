import subprocess
import os

def run_task(plan):
    try:
        cmd = plan.get("command")
        if not cmd:
            return "❌ No command specified in plan."
        if cmd.startswith("python "):
            subprocess.run(cmd.split(), check=True)
        elif cmd.endswith(".sh"):
            subprocess.run(["bash", cmd], check=True)
        else:
            subprocess.run(cmd, shell=True, check=True)
        return f"✅ Task executed: {cmd}"
    except Exception as e:
        return f"❌ Failed to run task: {e}" 