# Rock

Rock is a terminal-first local runtime for orchestrating multiple AI models, agents, skills and tools.

## V0.1

The first milestone implements the core multi-model council pipeline:

`prompt -> parallel providers -> normalize -> critique -> synthesis -> verification -> result`

### Current scope

- Python 3.12+
- Typer + Rich CLI
- Pydantic contracts
- Async provider abstraction
- LiteLLM gateway adapter
- OpenAI, Anthropic, DeepSeek, Perplexity, Gemini and Ollama configuration
- Mock mode for development without API keys
- SQLite session persistence
- Structured logging
- Retry, timeout and budget policies
- `rock doctor`
- Unit tests

### Deliberately out of scope for V0.1

GUI, voice, unrestricted terminal execution, browser automation, OpenHands, Deep Agents, LangGraph, A2A and Potencia AI integration.

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -e ".[dev]"

rock doctor
rock "Compare REST and GraphQL"
```

By default the command runs in deterministic mock mode when no provider keys are configured.

## Configuration

Copy `.env.example` to `.env` and configure the providers you want to enable.

Provider model names can be overridden through environment variables. Secrets must never be committed.

## Architecture

The Rock owns its internal contracts. External projects are adapters, not Rock's identity.

```
rock/
  src/rock/
    cli/
    config/
    core/
    providers/
    storage/
    observability/
  tests/
```
