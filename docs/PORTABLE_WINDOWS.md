# Rock V0.1 — Windows e pendrive

## Objetivo
Esta documentação prepara o Rock para uso em um pendrive. O código, ambiente virtual, configuração e banco podem ficar no pendrive. Provedores online continuam exigindo suas próprias credenciais.

## 1. Baixar
No PowerShell:

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

Preencha somente os provedores que pretende usar. Nunca publique .env.

## 4. Ollama
Instale o Ollama no Windows. Para guardar modelos na pasta do pendrive:

```powershell
$env:OLLAMA_MODELS="E:\ROCK-USB\models\ollama"
ollama pull llama3.2:3b
```

O modelo configurado em ROCK_OLLAMA_MODEL deve corresponder ao modelo baixado.

## 5. Teste sem APIs

```powershell
$env:ROCK_MODE="mock"
.\.venv\Scripts\rock.exe doctor
.\.venv\Scripts\rock.exe "Teste do Rock"
```

## 6. APIs reais
Configure as chaves no .env e use:

```
ROCK_MODE=live
```

Depois:

```powershell
.\.venv\Scripts\rock.exe doctor
.\.venv\Scripts\rock.exe providers
.\.venv\Scripts\rock.exe "Analise esta tarefa"
```

## 7. Superpowers
Defina ROCK_SUPERPOWERS_PATH apontando para um checkout local do Superpowers:

```powershell
$env:ROCK_SUPERPOWERS_PATH="E:\ROCK-USB\superpowers"
.\.venv\Scripts\rock.exe skills
```

O Rock lê skills no formato SKILL.md e as registra sem transformar o Superpowers no núcleo do runtime.

## 8. Chamar o Rock pelo pendrive

```powershell
E:\ROCK-USB\scripts\rock.ps1 "sua tarefa"
```

Para adicionar os scripts ao PATH apenas na sessão atual:

```powershell
. E:\ROCK-USB\scripts\install-path.ps1
rock "sua tarefa"
```

## 9. Iniciar

```powershell
E:\ROCK-USB\scripts\start.ps1
```

## 10. Diagnóstico

```powershell
rock doctor
rock providers
rock models
rock skills
rock sessions
```

## Segurança
- Não coloque chaves de API dentro dos scripts.
- Não faça commit de .env.
- Ações de efeito colateral passam por política de permissão.
- Faça backup do banco em data/ quando necessário.
