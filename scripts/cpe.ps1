# Windows wrapper: run the engine from a checkout without installing it (PowerShell 5+ or 7).
#   .\scripts\cpe.ps1 build examples\alvora\deck.json -o out\alvora.pptx
#   .\scripts\cpe.ps1 reason check work
# Rendering (render / run / eval) needs LibreOffice; without it, use --no-render or Docker (scripts/cpe-docker, via WSL).
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$Here\src;$env:PYTHONPATH" } else { "$Here\src" }
$env:PYTHONUTF8 = "1"
$Py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
if ($Py -eq "py") { & py -3 -m cpe @args } else { & $Py -m cpe @args }
exit $LASTEXITCODE
