Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MS Rewards Farm.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)

oLink.TargetPath = "d:\sao lưu E\MSrequat\.venv\Scripts\pythonw.exe"
oLink.Arguments = """d:\sao lưu E\MSrequat\launcher_gui.py"""
oLink.WorkingDirectory = "d:\sao lưu E\MSrequat"
oLink.IconLocation = "d:\sao lưu E\MSrequat\farm_icon.png"
oLink.WindowStyle = 1
oLink.Save
WScript.Echo "Success"
