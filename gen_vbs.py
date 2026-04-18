import codecs
import subprocess

vbs = """Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "C:\\Users\\HUYHOANG\\Desktop\\MS Farm.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "d:\\sao lưu E\\MSrequat\\.venv\\Scripts\\pythonw.exe"
oLink.Arguments = "\\"d:\\sao lưu E\\MSrequat\\launcher_gui.py\\""
oLink.WorkingDirectory = "d:\\sao lưu E\\MSrequat"
oLink.IconLocation = "d:\\sao lưu E\\MSrequat\\farm_icon.png"
oLink.WindowStyle = 1
oLink.Save
"""

with codecs.open('make_lnk.vbs', 'w', 'utf-16') as f:
    f.write(vbs)

print("VBS Generated")
