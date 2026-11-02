' Menjalankan perintah di latar TANPA jendela (dipakai Studio untuk autopilot & video panjang).
' Pemakaian: wscript.exe latar.vbs <file-log> <program> [argumen ...]
' Semua proses anak (claude, ffmpeg, node) ikut memakai console tersembunyi yang sama, dan keluarannya masuk ke file log.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
If WScript.Arguments.Count < 2 Then WScript.Quit 1
q = Chr(34)
perintah = ""
For i = 1 To WScript.Arguments.Count - 1
  perintah = perintah & " " & q & WScript.Arguments(i) & q
Next
sh.Run "cmd /c " & q & perintah & " > " & q & WScript.Arguments(0) & q & " 2>&1" & q, 0, False
