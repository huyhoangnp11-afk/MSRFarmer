import os
import shutil
from PIL import Image
import pythoncom
from win32com.shell import shell

# Path to the newly generated AI logo
source_image = r"C:\Users\HUYHOANG\.gemini\antigravity\brain\3b207762-54d2-443f-a182-80cb53637537\professional_app_icon_1776427001949.png"
dest_folder = r"d:\sao lưu E\MSrequat"

png_path = os.path.join(dest_folder, "farm_icon.png")
ico_path = os.path.join(dest_folder, "farm_icon.ico")

# 1. Resize and Create ICO
img = Image.open(source_image)
# Save as PNG
img.save(png_path)
# Save as ICO (multiple sizes for Windows)
img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])

# 2. Create Shortcuts
desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
cmd_path = os.path.join(os.environ['WINDIR'], 'System32', 'cmd.exe')

def create_shortcut(name, target_script, icon_file):
    path = os.path.join(desktop, name + ".lnk")
    shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    shortcut.SetPath(cmd_path)
    args = f'/c start "" "d:\sao lưu E\MSrequat\.venv\Scripts\pythonw.exe" "{target_script}"'
    shortcut.SetArguments(args)
    shortcut.SetWorkingDirectory(r"d:\sao lưu E\MSrequat")
    shortcut.SetShowCmd(7) # MINIMIZED
    shortcut.SetIconLocation(icon_file, 0)
    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(path, 0)

# Replace the old GUI shortcut
create_shortcut("MS Rewards GUI", r"d:\sao lưu E\MSrequat\launcher_gui.py", ico_path)

# Create the TRAY APP shortcut!
create_shortcut("MS Rewards Ngầm (Tray)", r"d:\sao lưu E\MSrequat\tray_app.py", ico_path)

print("LOGO AND SHORTCUTS CREATED")
