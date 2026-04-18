import subprocess
import os
import sys

# Get common paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pythonw = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
gui_script = os.path.join(BASE_DIR, "launcher_gui.py")
tray_script = os.path.join(BASE_DIR, "tray_app.py")

def launch_silent(script_path):
    if os.path.exists(script_path):
        # We use 'start' via shell to ensures it detaches and runs independently
        cmd = f'start "" "{pythonw}" "{script_path}"'
        subprocess.Popen(cmd, shell=True)

if __name__ == "__main__":
    # Launch both. Mutexes inside each script will prevent duplicates automatically.
    launch_silent(tray_script)
    launch_silent(gui_script)
    sys.exit(0)
