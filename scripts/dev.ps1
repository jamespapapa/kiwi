param(
  [switch]$Install
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

if ($Install) {
  if (!(Test-Path ".\.venv")) {
    python -m venv .venv
  }
  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  if ($env:OS -eq "Windows_NT") {
    .\.venv\Scripts\python.exe -m pip install pywinpty
  }
  npm install
}

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$Root\scripts\start-backend.ps1`""
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$Root\scripts\start-web.ps1`""

Write-Host "KIWI backend: http://localhost:8787"
Write-Host "KIWI web:     http://localhost:3000"
