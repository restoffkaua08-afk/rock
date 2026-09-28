# Rock V0.1 — Pendrive Windows

## O que fica no pendrive

```
ROCK-USB/
  rock/              # código + .venv + .env
  superpowers/       # baixado automaticamente
  scripts/           # launchers PowerShell
  models/             # opcional, modelos locais
```

## Preparação automática

Depois de colocar/clonar este repositório em `ROCK-USB\rock`:

```powershell
cd E:\ROCK-USB
.\scripts\setup.ps1 -InstallAgents -InstallOllama
.\scripts\install-path.ps1
rock doctor
```

O setup:
- cria o ambiente Python;
- instala o Rock e dependências;
- cria `.env`;
- pergunta apenas pelas chaves de API que ainda não estiverem configuradas;
- baixa/atualiza o Superpowers;
- configura o caminho do Superpowers;
- instala o Codex CLI se npm estiver disponível e `-InstallAgents` for usado;
- verifica Ollama;
- executa doctor/providers/skills.

O Superpowers é uma biblioteca de skills e metodologia para agentes; a instalação varia conforme o harness, por isso o Rock mantém o checkout separado e usa suas skills como fonte. citeturn0search1turn0search3

## Ollama

O Ollama possui instalador oficial para Windows e API local em `localhost:11434`. citeturn4search0turn4search3

Para instalar manualmente quando necessário:
```powershell
irm https://ollama.com/install.ps1 | iex
```

Depois:
```powershell
ollama pull llama3.2:3b
```

Para ferramentas de código, o Ollama atualmente documenta integrações com Claude Code, OpenCode e Codex via `ollama launch`. citeturn4search9

## Chamar o Rock

```powershell
E:\ROCK-USB\scripts\rock.ps1 "Analise meu projeto"
```

Ou:
```powershell
. E:\ROCK-USB\scripts\install-path.ps1
rock "Analise meu projeto"
```

## Atualizar

```powershell
.\scripts\update.ps1
```

O update baixa as alterações do GitHub, reinstala a versão local e atualiza o Superpowers.

## Credenciais

Chaves de API não são colocadas no GitHub. Elas ficam no `.env` local do pendrive. Se o pendrive for compartilhado, não mantenha chaves pessoais nele.
