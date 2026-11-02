' Dijalankan Windows Task Scheduler tiap jam: satu putaran autopilot Yofamo, tanpa jendela.
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = folder
sh.Run "cmd /c python agents\autopilot.py jalan > logs\autopilot-terakhir.txt 2>&1", 0, False
