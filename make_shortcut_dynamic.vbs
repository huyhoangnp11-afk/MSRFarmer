Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "C:\Users\HUYHOANG\Desktop\MS Rewards Trau.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
curDir = oWS.CurrentDirectory
oLink.TargetPath = curDir & "\.venv\Scripts\pythonw.exe"
oLink.Arguments = """" & curDir & "\launcher_gui.py"""
oLink.WorkingDirectory = curDir
oLink.IconLocation = curDir & "\farm_icon.png"
oLink.WindowStyle = 1
oLink.Save
