param([Parameter(Mandatory=$true,Position=0)][string]$Prompt,[string]$Mode="council")
$Root = Split-Path -Parent $PSScriptRoot
$Repo = $Root
Set-Location $Repo
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$RockExe = Join-Path $Repo ".venv\Scripts\rock.exe"
if (Test-Path $RockExe) {
  & $RockExe run $Prompt --mode $Mode
  exit $LASTEXITCODE
}
if (Test-Path $Python) {
  & $Python -m rock.cli.main run $Prompt --mode $Mode
  exit $LASTEXITCODE
}
Write-Error "Rock não está preparado. Execute scripts\setup.ps1."
exit 1
