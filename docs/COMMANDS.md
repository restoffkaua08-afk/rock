# Comandos Rock V0.1

## Preparação
A partir da pasta do pendrive:
```powershell
.\scripts\setup.ps1 -InstallAgents -InstallOllama
.\scripts\install-path.ps1
```

## Uso
```powershell
rock "pergunta"
rock run "pergunta"
rock ask "pergunta"
```

## Modos
```powershell
rock run "pergunta" --mode quick
rock run "pergunta" --mode council
rock run "pergunta" --mode deep
rock run "pergunta" --mode research
rock run "pergunta" --mode agent
```

## Agentes externos
```powershell
rock agents
rock agent codex "Analise e implemente a tarefa no diretório atual"
rock agent claude "Analise e implemente a tarefa no diretório atual"
```

O Codex CLI possui o modo não interativo `codex exec`, apropriado para automação. O Rock usa esse modo no adapter externo. citeturn1search0turn3search5

## Diagnóstico
```powershell
rock doctor
rock providers
rock models
rock skills
rock sessions
```

## Council
Task → modelos em paralelo → normalização → crítica → síntese → verificação → persistência.

### Selecionar modelos
Por padrão, o Rock usa todos os providers configurados. Para limitar o Council, defina no `.env`:
```text
ROCK_COUNCIL_MODELS=openai,anthropic,gemini
```
Os nomes aceitos são `openai`, `anthropic`, `deepseek`, `perplexity`, `gemini` e `ollama`. Os modelos individuais continuam configuráveis pelas variáveis `ROCK_<PROVIDER>_MODEL`.

O protocolo também pode ser configurado:
```text
ROCK_COUNCIL_PROTOCOL=parallel
ROCK_COUNCIL_ROUNDS=1
```
`parallel` executa o fluxo padrão. `critique_synthesis` permite repetir a crítica em múltiplas rodadas, limitado por `ROCK_COUNCIL_ROUNDS` e pelo orçamento da tarefa.

Falha de um provedor não derruba os demais.
