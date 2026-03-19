@echo off
cd /d "C:\Users\mathi\Documents\6. DATA PACE\0. Dashboard\Fichiers sources"
python generate_dashboard.py
git add .
git commit -m "Mise a jour %DATE:~0,10%"
git push
echo.
echo Dashboard mis a jour en ligne !
pause