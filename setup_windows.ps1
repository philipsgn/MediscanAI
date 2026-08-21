$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Write-Host "[1/4] Checking Python..."
py --version

if (-not (Test-Path $venvPython)) {
    Write-Host "[2/4] Creating virtual environment..."
    py -m venv (Join-Path $projectRoot ".venv")
} else {
    Write-Host "[2/4] Virtual environment already exists."
}

Write-Host "[3/4] Updating pip..."
& $venvPython -m pip install --upgrade pip --retries 5 --timeout 120

Write-Host "[4/4] Installing project libraries..."
& $venvPython -m pip install --no-cache-dir --retries 5 --timeout 120 -r (Join-Path $projectRoot "requirements.txt")

Write-Host ""
Write-Host "Completed successfully. Activate the environment with:"
Write-Host ".\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Checking Poppler..."
if (Get-Command pdftoppm -ErrorAction SilentlyContinue) {
    Write-Host "Poppler is installed."
    pdftoppm -h 2>&1 | Select-Object -First 1
} else {
    Write-Warning "Poppler was not found. Installing it with winget..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id oschwartz10612.Poppler -e --accept-source-agreements --accept-package-agreements
        Write-Host ""
        Write-Host "Poppler was installed. Close and reopen VS Code Terminal, then run:"
        Write-Host "pdftoppm -h"
    } else {
        Write-Warning "winget is not available. Install Poppler manually, then reopen VS Code."
        Write-Host "winget install --id oschwartz10612.Poppler -e"
    }
}
