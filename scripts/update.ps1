$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Repo = $Root
Set-Location $Repo
if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw "Git não encontrado." }
git pull --ff-only
if (!(Test-Path ".venv\Scripts\python.exe")) { & (Join-Path $PSScriptRoot "setup.ps1") ; exit $LASTEXITCODE }
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
$Superpowers = Join-Path $Root "superpowers"
if (Test-Path (Join-Path $Superpowers ".git")) { git -C $Superpowers pull --ff-only }
& ".\.venv\Scripts\python.exe" -m rock.cli.main doctor