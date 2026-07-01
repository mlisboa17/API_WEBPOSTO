@echo off
cd /d "%~dp0"
"C:\Program Files\Python314\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8040
