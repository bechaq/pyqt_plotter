Dim shell
Dim fso
Dim appDir
Dim pythonw
Dim scriptPath
Dim command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = "C:\Users\bench\AppData\Local\Programs\Python\Python311\pythonw.exe"
scriptPath = appDir & "\pyqt_plotter_main.pyw"
command = """" & pythonw & """ """ & scriptPath & """"

shell.CurrentDirectory = appDir
shell.Run command, 0, False
