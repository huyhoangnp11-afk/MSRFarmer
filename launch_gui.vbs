Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = strPath & "\.venv\Scripts\pythonw.exe"
If Not FSO.FileExists(pythonwPath) Then
    pythonwPath = "pythonw"
End If
WshShell.CurrentDirectory = strPath
WshShell.Run """" & pythonwPath & """ """ & strPath & "\launcher_gui.py""", 0, False
