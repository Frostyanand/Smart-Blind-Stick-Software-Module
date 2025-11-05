@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo Starting Smart Blind Stick...
C:\Users\anura\AppData\Local\Programs\Python\Python312\python.exe model.py
pause
