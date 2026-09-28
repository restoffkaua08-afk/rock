from __future__ import annotations

import asyncio
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel

from rock.config.settings import get_settings
from rock.core.contracts import Model, Policy, Session, Task, TaskMode
from rock.core.council import CouncilEngine
from rock.core.skills import SkillRegistry, default_skill_roots
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
    providers: dict[str, object] = {}
    models: dict[str, Model] = {}
    selected: list[str] = []

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


def _make_task(prompt: str, mode: TaskMode) -> Task:
    settings = get_settings()
    return Task(
        id=str(uuid4()),
        prompt=prompt,
        mode=mode,
        policy=Policy(
            timeout_seconds=settings.rock_timeout_seconds,
            max_retries=settings.rock_max_retries,
            budget={"max_parallel": settings.rock_max_parallel},
        ),
    )


def _run(prompt: str, mode: TaskMode, verbose: bool) -> None:
    configure_logging(verbose)
    settings = get_settings()
    task = _make_task(prompt, mode)
    engine, model_ids = build_engine()
    if not model_ids:
        raise typer.BadParameter(
            "No providers are configured. Use ROCK_MODE=mock or configure at least one API key."
        )

    store = SQLiteStore(settings.rock_db_path)
    store.save_task(task)
    session = Session(id=str(uuid4()), task_ids=[task.id])
    store.save_session(session)

    console.print(Panel.fit("ROCK V0.1", subtitle=f"{len(model_ids)} models"))
    synthesis, verification, responses = asyncio.run(engine.run(task, model_ids))
    store.save_run(task.id, responses, synthesis, verification)

    for response in responses:
        status = "✓" if not response.error else "✗"
        console.print(f"{status} {response.provider}/{response.model}")
    console.print(Panel(synthesis, title="Synthesis"))
    console.print(
        f"Verification: {'PASSED' if verification.passed else 'FAILED'} "
        f"(confidence={verification.confidence})"
    )


@app.command("run")
def run(
    prompt: str = typer.Argument(...),
    mode: TaskMode = typer.Option(TaskMode.COUNCIL, "--mode", "-m"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run a task through Rock's council."""
    _run(prompt, mode, verbose)


@app.command("ask")
def ask(
    prompt: str = typer.Argument(...),
    mode: TaskMode = typer.Option(TaskMode.COUNCIL, "--mode", "-m"),
) -> None:
    """Alias for rock run."""
    _run(prompt, mode, False)


@app.command()
def providers() -> None:
    """Show configured providers."""
    settings = get_settings()
    rows = [
        ("OpenAI", settings.openai_api_key, settings.rock_openai_model),
        ("Anthropic", settings.anthropic_api_key, settings.rock_anthropic_model),
        ("DeepSeek", settings.deepseek_api_key, settings.rock_deepseek_model),
        ("Perplexity", settings.perplexity_api_key, settings.rock_perplexity_model),
        ("Gemini", settings.gemini_api_key, settings.rock_gemini_model),
        ("Ollama", True, settings.rock_ollama_model),
    ]
    for name, configured, model in rows:
        console.print(f"{'✓' if configured else '○'} {name}: {model}")


@app.command()
def models() -> None:
    """Show the model map currently configured for Rock."""
    providers()


@app.command()
def skills() -> None:
    """Discover Rock and Superpowers skills."""
    registry = SkillRegistry(default_skill_roots())
    found = registry.discover()
    if not found:
        console.print("No skills found.")
        return
    for skill in found.values():
        console.print(f"✓ {skill.id} [{skill.source}]")


@app.command()
def sessions() -> None:
    """Show stored session/task database location."""
    settings = get_settings()
    console.print(f"SQLite: {settings.rock_db_path}")


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
    console.print("✓ Skill roots:")
    for root in default_skill_roots():
        console.print(f"  - {root}")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
