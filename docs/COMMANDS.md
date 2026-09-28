# Comandos Rock V0.1

## Direto
```powershell
rock "pergunta"
```

## Explícito
```powershell
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

## Operação
```powershell
rock doctor
rock providers
rock models
rock skills
rock sessions
```

## Council
1. Cria Task.
2. Consulta os modelos em paralelo.
3. Normaliza respostas.
4. Faz crítica cruzada.
5. Faz síntese.
6. Verifica a síntese.
7. Persiste o resultado no SQLite.

Falha de um provedor não derruba os demais.
