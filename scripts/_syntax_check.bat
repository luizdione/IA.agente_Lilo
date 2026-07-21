@echo off
cd /d "%~dp0.."
if exist logs\pyc.rc del /q logs\pyc.rc
python -m py_compile agents\villa_lobos\agent.py 2> logs\pyc.err && echo OK> logs\pyc.rc || echo FAIL> logs\pyc.rc
