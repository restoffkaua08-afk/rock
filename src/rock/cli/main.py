from __future__ import annotations

import asyncio
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel

from rock.config.settings import get_settings
from rock.core.contracts import Model, Policy, Task, TaskMode, Session
from rock.core.council import CouncilEngine
from rock.observability.logging import configure_logging
from rock.providers.litellm_provider import LiteLLMProvider
from rock.providers.mock import MockProvider
from rock.storage.sqlite import SQLiteStore

app = typer.Typer(help="Rock — terminal-first AI orchestration runtime.")
console = Console()


def build_engine() -> tuple[CouncilEngine, list[str]]:
    settings = get_settings()
    definitions = [
        ("openai", settings.rock_openai_model, settings.openai_api_key),
        ("anthropic", settings.rock_anthropic_model, settings.anthropic_api_key),
        ("deepseek", settings.rock_deepseek_model, settings.deepseek_api_key),
        ("perplexity", settings.rock_perplexity_model, settings.perplexity_api_key),
        ("gemini", settings.rock_gemini_model, settings.gemini_api_key),
        ("ollama", settings.rock_ollama_model, True),
    ]
    providers = {}
    models = {}
    selected = []

    for provider_name, model_name, configured in definitions:
        if settings.rock_mode.lower() == "mock":
            provider = MockProvider(provider_name)
        elif configured:
            provider = LiteLLMProvider(provider_name)
        else:
            continue
        providers[provider_name] = provider
        model_id = f"{provider_name}:default"
        models[model_id] = Model(id=model_id, provider=provider_name, model_name=model_name)
        selected.append(model_id)

    return CouncilEngine(providers, models), selected


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Task to send to Rock."),
    mode: TaskMode = typer.Option(TaskMode.COUNCIL, "--mode", "-m"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run a Rock task through the V0.1 council pipeline."""
    configure_logging(verbose)
    settings = get_settings()
    task = Task(
        id=str(uuid4()),
        prompt=prompt,
        mode=mode,
        policy=Policy(
            timeout_seconds=settings.rock_timeout_seconds,
            max_retries=settings.rock_max_retries,
        ),
    )
    engine, model_ids = build_engine()
    if not model_ids:
        raise typer.BadParameter("No providers are configured. Use ROCK_MODE=mock or configure an API key.")

    store = SQLiteStore(settings.rock_db_path)
    store.save_task(task)
    session = Session(id=str(uuid4()), task_ids=[task.id])
    store.save_session(session)

    console.print(Panel.fit("ROCK V0.1", subtitle=f"{len(model_ids)} providers"))
    synthesis, verification, responses = asyncio.run(engine.run(task, model_ids))
    store.save_run(task.id, responses, synthesis, verification)

    console.print()
    for response in responses:
        status = "✓" if not response.error else "✗"
        console.print(f"{status} {response.provider}/{response.model}")
    console.print()
    console.print(Panel(synthesis, title="Synthesis"))
    console.print(
        f"Verification: {'PASSED' if verification.passed else 'FAILED'} "
        f"(confidence={verification.confidence})"
    )


@app.command()
def doctor() -> None:
    """Check the local Rock runtime and configured providers."""
    settings = get_settings()
    console.print(Panel.fit("ROCK DOCTOR"))
    console.print("✓ Python runtime detected")
    console.print(f"✓ Mode: {settings.rock_mode}")
    console.print(f"✓ SQLite: {settings.rock_db_path}")
    keys = {
        "OpenAI": settings.openai_api_key,
        "Anthropic": settings.anthropic_api_key,
        "DeepSeek": settings.deepseek_api_key,
        "Perplexity": settings.perplexity_api_key,
        "Gemini": settings.gemini_api_key,
    }
    for name, value in keys.items():
        console.print(f"{'✓' if value else '○'} {name}: {'configured' if value else 'not configured'}")
    console.print(f"✓ Ollama endpoint: {settings.ollama_base_url}")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
