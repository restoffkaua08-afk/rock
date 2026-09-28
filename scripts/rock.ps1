param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$RockExe = Join-Path $Root ".venv\Scripts\rock.exe"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $RockExe) {
    & $RockExe @Prompt
} elseif (Test-Path $Python) {
    $env:PYTHONPATH = Join-Path $Root "src"
    & $Python -m rock @Prompt
} else {
    Write-Error "Rock não está preparado. Execute scripts\setup.ps1."
    exit 1
}
exit $LASTEXITCODE
