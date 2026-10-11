$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$LocalPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$Python = if (Test-Path -LiteralPath $LocalPython) { $LocalPython } else { 'python' }
& $Python -m unittest discover -s tests -v

