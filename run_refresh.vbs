' Windowless launcher for Task Scheduler — avoids the console-window flash.
' Task Scheduler action:  wscript.exe "C:\Users\USER\OneDrive\Desktop\linkedin-content-lab\run_refresh.vbs"
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\USER\OneDrive\Desktop\linkedin-content-lab"
' window style 0 = hidden (no flash); True = wait for completion. Logs to refresh.log.
' Runs the refresh AND pushes results to GitHub so the live Pages site updates.
sh.Run "cmd /c ""C:\Users\USER\OneDrive\Desktop\linkedin-content-lab\refresh_and_publish.bat"" > refresh.log 2>&1", 0, True
