<#
.SYNOPSIS
    Set up Python virtual environment and install project in editable mode with dev dependencies.

.DESCRIPTION
    - Creates a .venv virtual environment at project root
    - Activates the virtual environment
    - Upgrades pip
    - Installs the project using `pip install -e .[dev]`

.REQUIREMENTS
    - Python 3.11+ available in PATH
    - PowerShell execution policy allows local scripts
#>

$ErrorActionPreference = "Stop"

Write-Host "==> Starting Python environment setup..."

# Resolve project root (script is expected to be in scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

Set-Location $ProjectRoot

# Check Python availability
Write-Host "==> Checking Python installation..."
python --version

# Create virtual environment if it does not exist
if (-Not (Test-Path ".venv")) {
    Write-Host "==> Creating virtual environment (.venv)..."
    python -m venv .venv
} else {
    Write-Host "==> Virtual environment already exists (.venv)"
}

# Activate virtual environment
Write-Host "==> Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "==> Upgrading pip..."
python -m pip install --upgrade pip

# Install project in editable mode with dev dependencies
Write-Host "==> Installing project in editable mode with dev dependencies..."
pip install -e ".[dev]"

Write-Host "==> Environment setup complete."
Write-Host "==> Virtual environment: .venv"
Write-Host "==> You can now run Python or invoke the ingest module."
