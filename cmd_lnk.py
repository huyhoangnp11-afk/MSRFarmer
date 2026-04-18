import os
import pythoncom
from win32com.shell import shell

desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
path = os.path.join(desktop, 'MS Rewards GUI.lnk')
cmd_path = os.path.join(os.environ['WINDIR'], 'System32', 'cmd.exe')

shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
shortcut.SetPath(cmd_path)

# This argument line passes the exact paths to start
args = r'/c start "" "d:\sao lưu E\MSrequat\.venv\Scripts\pythonw.exe" "d:\sao lưu E\MSrequat\launcher_gui.py"'
shortcut.SetArguments(args)
shortcut.SetWorkingDirectory(r'd:\sao lưu E\MSrequat')
shortcut.SetShowCmd(7) # MINIMIZED
shortcut.SetIconLocation(r'd:\sao lưu E\MSrequat\farm_icon.png', 0)

persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
persist_file.Save(path, 0)
print('SUCCESS_CMD_LNK')
