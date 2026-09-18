$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvStreamlit = Join-Path $PSScriptRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $venvStreamlit)) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv .venv
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

Write-Host "Starting Orcadash with: $venvPython"
& $venvStreamlit run streamlit_app\app.py
