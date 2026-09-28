param(
  [switch]$InstallAgents,
  [switch]$InstallOllama
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Repo = $Root
$Superpowers = Join-Path $Root "superpowers"

function Write-Step($Text) {
  Write-Host ""
  Write-Host "=== $Text ===" -ForegroundColor Cyan
}

if (!(Test-Path $Repo)) { throw "Diretório Rock não encontrado: $Repo" }
Set-Location $Repo

Write-Step "Verificando Python"
$python = Get-Command python -ErrorAction SilentlyContinue
if (!$python) { throw "Python 3.12+ não encontrado." }
$version = python -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))"
if ([version]$version -lt [version]"3.12") { throw "Rock exige Python 3.12+; encontrado $version." }

Write-Step "Criando ambiente Python"
if (!(Test-Path ".venv")) { python -m venv .venv }
$Py = Join-Path $Repo ".venv\\Scripts\\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -e ".[dev]"

Write-Step "Configurando .env"
if (!(Test-Path ".env")) { Copy-Item ".env.example" ".env" }

function Set-EnvValue($Name, $Value) {
  $path = Join-Path $Repo ".env"
  $lines = @(Get-Content $path -ErrorAction SilentlyContinue)
  $found = $false
  $escaped = [regex]::Escape($Name)
  for ($i=0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^$escaped=") {
      $lines[$i] = "$Name=$Value"
      $found = $true
      break
    }
  }
  if (!$found) { $lines += "$Name=$Value" }
  Set-Content -Path $path -Value $lines -Encoding UTF8
}

$keys = @("OPENAI_API_KEY","ANTHROPIC_API_KEY","DEEPSEEK_API_KEY","PERPLEXITY_API_KEY","GEMINI_API_KEY")
$hasOnlineProvider = $false
foreach ($key in $keys) {
  $existing = [Environment]::GetEnvironmentVariable($key)
  if ($existing) {
    Set-EnvValue $key $existing
    $hasOnlineProvider = $true
    continue
  }
  $current = Get-Content ".env" | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
  if ($current -and $current.Substring($key.Length + 1).Trim()) {
    $hasOnlineProvider = $true
    continue
  }
  $secure = Read-Host "Chave $key (Enter para pular)" -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
  if ($value) {
    Set-EnvValue $key $value
    $hasOnlineProvider = $true
  }
}

if ($hasOnlineProvider) {
  Set-EnvValue "ROCK_MODE" "live"
} else {
  Set-EnvValue "ROCK_MODE" "mock"
  Write-Host "Nenhuma chave online configurada; mantendo ROCK_MODE=mock." -ForegroundColor Yellow
}
Set-EnvValue "ROCK_DB_PATH" ".rock/sessions.db"
Set-EnvValue "ROCK_TIMEOUT_SECONDS" "120"

Write-Step "Instalando Superpowers"
if (Get-Command git -ErrorAction SilentlyContinue) {
  if (Test-Path (Join-Path $Superpowers ".git")) {
    git -C $Superpowers pull --ff-only
  } elseif (!(Test-Path $Superpowers)) {
    git clone https://github.com/obra/Superpowers.git $Superpowers
  }
  Set-EnvValue "ROCK_SUPERPOWERS_PATH" $Superpowers
} else {
  Write-Warning "Git não encontrado; Superpowers não foi baixado."
}

if ($InstallAgents) {
  Write-Step "Instalando agentes CLI"
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (!(Get-Command codex -ErrorAction SilentlyContinue)) {
      npm install -g @openai/codex@alpha
    }
    if (Get-Command claude -ErrorAction SilentlyContinue) {
      Write-Host "Claude Code detectado."
    } else {
      Write-Host "Claude Code não detectado; ele pode ser instalado separadamente."
    }
  } else {
    Write-Warning "npm não encontrado; Codex não foi instalado."
  }
}

if ($InstallOllama) {
  Write-Step "Verificando Ollama"
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Ollama detectado."
    ollama list
  } else {
    Write-Warning "Ollama não está instalado; a instalação do serviço do sistema é mantida explícita."
  }
}

Write-Step "Verificação final"
& $Py -m rock.cli.main doctor
& $Py -m rock.cli.main providers
& $Py -m rock.cli.main skills

Write-Host ""
Write-Host "Rock preparado." -ForegroundColor Green
Write-Host "Use: .\\scripts\\install-path.ps1"
Write-Host "Depois: rock ""sua tarefa"""
