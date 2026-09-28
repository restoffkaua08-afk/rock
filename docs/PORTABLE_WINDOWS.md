# Rock V0.9 — Portable Windows Runtime

## Estrutura

```
ROCK-USB/
  rock/          # repositório do Rock
  superpowers/   # checkout opcional das skills
  scripts/       # launchers PowerShell
  .venv/         # ambiente Python local
  .env           # credenciais locais, nunca versionadas
  .rock/         # SQLite e estado local
```

## Preparar

Na raiz do repositório:

```powershell
.\scripts\setup.ps1
```

Opcionalmente:

```powershell
.\scripts\setup.ps1 -InstallAgents -InstallOllama
```

O setup cria o ambiente Python, instala o pacote, cria .env a partir do exemplo, configura Superpowers quando Git está disponível e executa verificações finais.

## Usar

```powershell
.\scripts\rock.ps1 "Analise este projeto"
```

Ou, para a sessão atual:

```powershell
. .\scripts\install-path.ps1
rock doctor
rock "Analise este projeto"
```

## Atualizar

```powershell
.\scripts\update.ps1
```

A atualização usa `git pull --ff-only`, reinstala o pacote e executa `doctor`.

## Portabilidade

O runtime é portátil em nível de projeto: código, ambiente Python, configuração local e SQLite podem acompanhar uma pasta/repositório. APIs externas continuam dependendo de credenciais e rede disponíveis.

Não há executável Windows compilado neste milestone; isso permanece fora do V0.9.
