param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

if (Test-Path ".\.venv\Scripts\python.exe") {
  $Python = ".\.venv\Scripts\python.exe"
} else {
  $Python = "python"
}

& $Python -m uvicorn app.main:app --app-dir backend --host $HostName --port $Port --reload
