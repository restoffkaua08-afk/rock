# Contributing to Rock

Obrigado por contribuir com o Rock.

## Antes de abrir uma mudança

1. Mantenha o escopo compatível com a versão atual.
2. Não introduza acesso irrestrito ao sistema operacional.
3. Preserve os contratos internos de Task, Model, Provider, Council, Evidence e Verification.
4. Adicione ou atualize testes para comportamento novo ou corrigido.

## Validação local

Execute `pip install -e ".[dev]`, `ruff check .` e `pytest`.

Uma mudança só deve ser considerada pronta quando os validadores passam.

## Pull requests

Descreva o problema resolvido, mudanças arquiteturais, testes e limitações conhecidas.
Não inclua chaves de API, dados pessoais ou arquivos de sessão em commits.
