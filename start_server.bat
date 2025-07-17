@echo off
setlocal enabledelayedexpansion

echo 🌐 Starting Flask app...
start "" python app.py

timeout /t 3 > nul

echo 🚪 Starting ngrok tunnel on reserved domain...
start "" ngrok http 5000 --domain=precise-crisp-pheasant.ngrok-free.app

timeout /t 5 > nul

REM Copy reserved domain to clipboard
echo https://precise-crisp-pheasant.ngrok-free.app | clip

echo ✅ Server is live at: https://precise-crisp-pheasant.ngrok-free.app
echo 📋 (URL copied to clipboard)

pause
