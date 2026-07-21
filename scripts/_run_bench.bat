@echo off
cd /d "%~dp0.."
if not exist logs mkdir logs
if exist logs\bench_done.flag del /q logs\bench_done.flag
set LILO_SERVER_PROFILE=desktop_dev
python scripts\bench_semantic_domains.py --iters 1,2,3 --timeout 300 > logs\bench_run.log 2>&1
echo DONE %ERRORLEVEL% > logs\bench_done.flag
