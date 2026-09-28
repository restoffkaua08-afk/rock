$Root = Split-Path -Parent $PSScriptRoot
$RockExe = Join-Path $Root ".venv\Scripts\rock.exe"
if (!(Test-Path $RockExe)) { & (Join-Path $PSScriptRoot "setup.ps1") }
if (!(Test-Path $RockExe)) { exit 1 }
& $RockExe doctor
Write-Host ""
Write-Host "Rock pronto. Exemplo:"
Write-Host "& '$PSScriptRoot\rock.ps1' 'analise esta tarefa'"