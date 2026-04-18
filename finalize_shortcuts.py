import os
import pythoncom
from win32com.shell import shell

# Configuration
dest_folder = r"d:\sao lưu E\MSrequat"
ico_path = os.path.join(dest_folder, "farm_icon.ico")
desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
cmd_path = os.path.join(os.environ['WINDIR'], 'System32', 'cmd.exe')
pythonw = os.path.join(dest_folder, ".venv", "Scripts", "pythonw.exe")

# Clean up ALL old/bad shortcuts FIRST
bad_shortcut_names = [
    "MS Rewards Farm.lnk",
    "MS Rewards Trau.lnk",
    "MS Farm.lnk",
    "MS Rewards GUI.lnk",
    "MS Rewards Ngầm (Tray).lnk",
    "MS Rewards Ng?m (Tray).lnk",
    "launcher_gui - Shortcut.lnk",
    "MSR-Management-Console.lnk",
    "MSR-Automation-Service.lnk"
]

for name in bad_shortcut_names:
    p = os.path.join(desktop, name)
    if os.path.exists(p):
        try: os.remove(p)
        except: pass

def create_native_shortcut(lnk_name, target_script):
    lnk_path = os.path.join(desktop, lnk_name)
    
    # We use the CMD trick to handle spaces and unicode in the folder path perfectly
    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    
    # Target: CMD.exe (standard system path)
    shortcut.SetPath(cmd_path)
    
    # Arguments: /c start "" "pythonw_path" "script_path"
    # we wrap everything in double quotes inside the single string
    args = f'/c start "" "{pythonw}" "{target_script}"'
    shortcut.SetArguments(args)
    
    # Set work dir to the root folder
    shortcut.SetWorkingDirectory(dest_folder)
    
    # Run Minimized (so no CMD window flashes)
    shortcut.SetShowCmd(7)
    
    # Set the premium ICO
    shortcut.SetIconLocation(ico_path, 0)
    
    # Save
    persist = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
    persist.Save(lnk_path, 0)

# Create the Master Hub shortcut that opens EVERYTHING
create_native_shortcut("MSR-Automation-Hub.lnk", os.path.join(dest_folder, "MSR_Smart_Launcher.py"))

print("PROFESSIONAL_SHORTCUTS_COMPLETE")
