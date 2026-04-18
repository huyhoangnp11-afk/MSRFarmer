import os
import pythoncom
from win32com.shell import shell

desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
path = os.path.join(desktop, "MS Rewards GUI.lnk")

# Clean up broken shortcuts from earlier
for bad_lnk in ["MS Farm.lnk", "MS Rewards Trau.lnk", "MS Rewards Farm.lnk", "MS Rewards GUI.lnk"]:
    bad_path = os.path.join(desktop, bad_lnk)
    if os.path.exists(bad_path):
        try: os.remove(bad_path)
        except: pass

# Create using IShellLink (Unicode safe!)
shortcut = pythoncom.CoCreateInstance(
    shell.CLSID_ShellLink, None,
    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
)

shortcut.SetPath(r"d:\sao lưu E\MSrequat\.venv\Scripts\pythonw.exe")
shortcut.SetArguments(r'"d:\sao lưu E\MSrequat\launcher_gui.py"')
shortcut.SetWorkingDirectory(r"d:\sao lưu E\MSrequat")
shortcut.SetIconLocation(r"d:\sao lưu E\MSrequat\farm_icon.png", 0)

# Save
persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
persist_file.Save(path, 0)

print("SUCCESS_ISHELLLINK")
