# Rock V0.1 — Windows e pendrive

Esta documentação prepara o Rock para uso em um pendrive. O código, ambiente virtual, configuração e banco podem ficar no pendrive. Provedores online continuam exigindo suas próprias credenciais.

## 1. Baixar
```powershell
cd E:\
git clone https://github.com/restoffkaua08-afk/rock.git ROCK-USB\rock
cd E:\ROCK-USB\rock
```
Troque E: pela letra do pendrive.

## 2. Python
Use Python 3.12+:
```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 3. Configuração
```powershell
Copy-Item .env.example .env
notepad .env
```
Preencha somente os provedores usados. Nunca publique `.env`.

## 4. Ollama
Para guardar modelos na pasta do pendrive:
```powershell
$env:OLLAMA_MODELS="E:\ROCK-USB\models\ollama"
ollama pull llama3.2:3b
```

## 5. Teste sem APIs
```powershell
$env:ROCK_MODE="mock"
.\.venv\Scripts\rock.exe doctor
.\.venv\Scripts\rock.exe "Teste do Rock"
```

## 6. APIs reais
Configure as chaves no `.env`, use `ROCK_MODE=live` e execute:
```powershell
.\.venv\Scripts\rock.exe doctor
.\.venv\Scripts\rock.exe providers
.\.venv\Scripts\rock.exe "Analise esta tarefa"
```

## 7. Superpowers
```powershell
$env:ROCK_SUPERPOWERS_PATH="E:\ROCK-USB\superpowers"
.\.venv\Scripts\rock.exe skills
```
O Rock descobre skills no formato `SKILL.md`.

## 8. Chamar pelo pendrive
```powershell
E:\ROCK-USB\scripts\rock.ps1 "sua tarefa"
```
Para adicionar os scripts ao PATH somente na sessão atual:
```powershell
. E:\ROCK-USB\scripts\install-path.ps1
rock "sua tarefa"
```

## 9. Diagnóstico
```powershell
rock doctor
rock providers
rock models
rock skills
rock sessions
```

## Segurança
Não coloque chaves dentro dos scripts nem faça commit de `.env`. Ações de efeito colateral passam pela política de permissões.
