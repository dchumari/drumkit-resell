@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo ================================================== >> logs\bot_process.log
echo [%date% %time%] Starting Storefront Bot Daemon... >> logs\bot_process.log
:loop
uv run python src/bot.py >> logs\bot_process.log 2>&1
echo [%date% %time%] Storefront Bot exited. Restarting in 5 seconds... >> logs\bot_process.log
timeout /t 5 > nul
goto loop
