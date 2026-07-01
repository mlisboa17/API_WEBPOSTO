$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$python = "C:\Program Files\Python314\python.exe"
$log = Join-Path $PSScriptRoot "president-dashboard-8040.log"

& $python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 *> $log
