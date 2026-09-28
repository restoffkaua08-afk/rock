$ErrorActionPreference="Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Repo = Join-Path $Root "rock"
if (!(Test-Path $Repo)) { throw "Diretório rock não encontrado em $Repo" }
Set-Location $Repo
python --version
if (!(Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
if (!(Test-Path ".env") -and (Test-Path ".env.example")) { Copy-Item ".env.example" ".env" }
Write-Host "Instalação concluída. Edite $Repo\.env e execute scripts\start.ps1."
