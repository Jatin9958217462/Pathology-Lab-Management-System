@echo off
chcp 65001 >nul
title PathLab - Lab Management System

:: ============================================================
::  PathLab — START SCRIPT (Windows)
::  Yahan se aap decide kar sakte hain database kahan se load ho
:: ============================================================

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        PathLab Lab Management System         ║
echo  ║           Starting... Please wait            ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ------------------------------------------------------------
:: DB PATH CONFIGURATION
:: Neeche se ek option UNCOMMENT karein (:: hatao line se)
:: ------------------------------------------------------------

:: [OPTION 1] Default — Project folder mein hi database (sabse simple)
::   (kuch mat karein, aise hi chhod do)

:: [OPTION 2] Pendrive mein database
::   (E: ki jagah apni pendrive drive letter likhein)
:: set PATHLAB_DB_PATH=E:\pathlab_data\db.sqlite3
:: set PATHLAB_MEDIA_PATH=E:\pathlab_data\media

:: [OPTION 3] Network Server / Shared Folder
::   (\\SERVER\share ki jagah apna network path likhein)
:: set PATHLAB_DB_PATH=\\192.168.1.100\pathlab\db.sqlite3
:: set PATHLAB_MEDIA_PATH=\\192.168.1.100\pathlab\media

:: [OPTION 4] Kisi bhi custom path mein
:: set PATHLAB_DB_PATH=C:\Users\Jatin\Desktop\pathlab_data\db.sqlite3
:: set PATHLAB_MEDIA_PATH=C:\Users\Jatin\Desktop\pathlab_data\media

:: ------------------------------------------------------------

:: Project directory mein jao
cd /d "%~dp0"

:: Python check
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nahi mila! Python 3.10+ install karein.
    pause
    exit /b 1
)

:: Dependencies install (pehli baar ya update ke liye)
echo [1/3] Dependencies check kar raha hai...
pip install -r requirements.txt -q

:: Migration run karo (naya field ya table automatically ban jayega)
echo [2/3] Database update kar raha hai...
python manage.py migrate --run-syncdb -v 0

:: Server start karo
echo [3/3] Server shuru ho raha hai...
echo.
echo  ✅ PathLab chalu hai!
echo  🌐 Browser mein kholein: http://127.0.0.1:8000
echo  📁 Database: %PATHLAB_DB_PATH%
if defined PATHLAB_DB_PATH (
    echo  📁 Database: %PATHLAB_DB_PATH%
) else (
    echo  📁 Database: Project folder (db.sqlite3)
)
echo.
echo  Sabhi computers ek hi database use kar sakte hain
echo  agar PATHLAB_DB_PATH same shared path pe set ho.
echo.
echo  Band karne ke liye: Ctrl+C dabayein
echo  ─────────────────────────────────────────────
echo.

python manage.py runserver 0.0.0.0:8000

pause
