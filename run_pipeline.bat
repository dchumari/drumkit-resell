@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo ================================================== >> logs\pipeline_process.log
echo [%date% %time%] Running Uploader Pipeline... >> logs\pipeline_process.log
uv run python src/pipeline.py --upload >> logs\pipeline_process.log 2>&1
echo [%date% %time%] Pipeline completed. >> logs\pipeline_process.log
