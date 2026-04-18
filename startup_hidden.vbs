Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = strPath & "\.venv\Scripts\pythonw.exe"

If Not FSO.FileExists(pythonwPath) Then
    pythonwPath = "pythonw"
End If

' Delay startup a bit so Windows/network finishes settling down.
WScript.Sleep 120000

WshShell.CurrentDirectory = strPath
WshShell.Run """" & pythonwPath & """ """ & strPath & "\tray_app.py""", 0, False
