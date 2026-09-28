# Rock V0.1 Architecture

```text
CLI → Task → Council Engine
             ├─ Provider adapters: OpenAI / Anthropic / DeepSeek / Perplexity / Gemini / Ollama
             ├─ Critic
             ├─ Synthesizer
             ├─ Verifier
             ├─ Agent runtime
             ├─ Skill registry / Superpowers
             ├─ Permission engine / Tools
             └─ SQLite / logs
```

Contratos pertencem ao Rock. Providers são adapters. Superpowers é fonte de skills, não o núcleo. Modelos não recebem autoridade implícita para efeitos colaterais. Concordância não é prova de verdade; verificação é uma etapa própria.
