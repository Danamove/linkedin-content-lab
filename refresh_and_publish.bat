@echo off
REM Weekly job: refresh data, then publish to GitHub so the live Pages site updates.
cd /d "C:\Users\USER\OneDrive\Desktop\linkedin-content-lab"
echo [%DATE% %TIME%] refresh start
python refresh.py
git add -A
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "weekly refresh"
  git push
  echo [%DATE% %TIME%] published
) else (
  echo [%DATE% %TIME%] no changes to publish
)
