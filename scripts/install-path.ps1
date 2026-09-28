$Root = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $Root ".venv\Scripts"
$env:PATH = "$Bin;$PSScriptRoot;$env:PATH"
Write-Host "Rock adicionado ao PATH desta sessão."
Write-Host "Use: rock 'sua tarefa'"