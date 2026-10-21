$ErrorActionPreference = "Stop"

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $dir ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    python -m venv $venv
}

& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r (Join-Path $dir "requirements.txt") --quiet
& $python (Join-Path $dir "voicebridge.py") @args

