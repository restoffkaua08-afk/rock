$Root = Split-Path -Parent $PSScriptRoot
$env:PATH = (Join-Path $Root ".venv\Scripts") + ";" + $env:PATH
$env:PYTHONPATH = Join-Path $Root "src"
Write-Host "Rock PATH configurado para esta sessão do PowerShell."
Write-Host "Teste: rock doctor"
