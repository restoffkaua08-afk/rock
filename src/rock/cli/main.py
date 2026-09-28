from __future__ import annotations

import asyncio
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel
from typer.core import TyperGroup

from rock.agents.cli_agents import ExternalAgentRunner
from rock.cli.terminal_ui import RockTerminalUI, interactive_prompt
from rock.config.settings import get_settings
from rock.core.agent import AgentRuntime
from rock.core.contracts import Agent, Model, Policy, Session, Task, TaskMode
from rock.core.council import CouncilEngine
from rock.core.providers import Provider
from rock.core.skills import SkillRegistry, default_skill_roots
from rock.observability.events import SQLiteEventSink, TaskEventAdapter
from rock.observability.logging import configure_logging
from rock.providers.litellm_provider import LiteLLMProvider
from rock.providers.mock import MockProvider
from rock.storage.sqlite import SQLiteStore


class RockGroup(TyperGroup):
    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        if args and not args[0].startswith("-") and args[0] not in self.commands:
            args = ["run", *args]
        return super().parse_args(ctx, args)


app = typer.Typer(
    cls=RockGroup,
    help="Rock — terminal-first AI orchestration runtime.",
)
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
    providers: dict[str, Provider] = {}
    models: dict[str, Model] = {}
    selected: list[str] = []
    requested = (
        {name.strip().lower() for name in settings.rock_council_models.split(",") if name.strip()}
        if settings.rock_council_models
        else None
    )

    for provider_name, model_name, configured in definitions:
        if requested is not None and provider_name not in requested:
            continue
        if settings.rock_mode.lower() == "mock":
            provider = MockProvider(provider_name)
        elif configured:
            provider = LiteLLMProvider(
                provider_name,
                api_key=configured if isinstance(configured, str) else None,
                api_base=settings.ollama_base_url if provider_name == "ollama" else None,
            )
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
            budget={
                "max_parallel": settings.rock_max_parallel,
                "max_cost": settings.rock_max_cost,
                "max_rounds": settings.rock_council_rounds,
            },
        ),
        metadata={
            "council_protocol": settings.rock_council_protocol,
            "council_critic_model": settings.rock_council_critic_model,
            "council_synthesizer_model": settings.rock_council_synthesizer_model,
            "council_verifier_model": settings.rock_council_verifier_model,
            "council_judge_model": settings.rock_council_judge_model,
            "council_red_team_model": settings.rock_council_red_team_model,
            "council_voter_model": settings.rock_council_voter_model,
        },
    )


def _run(prompt: str, mode: TaskMode, verbose: bool, agent_names: list[str] | None = None) -> None:
    configure_logging(verbose)
    settings = get_settings()
    task = _make_task(prompt, mode)

    if mode == TaskMode.AGENT:
        runner = ExternalAgentRunner()
        available = {a.name for a in runner.available()}
        names = agent_names or sorted(available)
        names = [name for name in names if name in available]
        if not names:
            raise typer.BadParameter("Nenhum agente externo disponível. Use rock agents.")

        async def run_agents():
            return await asyncio.gather(
                *[runner.run(name, prompt, task_id=str(uuid4())) for name in names]
            )

        executions = asyncio.run(run_agents())
        for execution in executions:
            console.print(
                Panel(
                    execution.output.get("stdout", "") or execution.error or "",
                    title=f"Agent: {execution.actor} [{execution.status.value}]",
                )
            )
        return

    engine, model_ids = build_engine()
    if not model_ids:
        raise typer.BadParameter(
            "No providers are configured. Use ROCK_MODE=mock or configure at least one API key."
        )

    store = SQLiteStore(settings.rock_db_path)
    store.save_task(task)
    session = Session(id=str(uuid4()), task_ids=[task.id])
    store.save_session(session)

    ui = RockTerminalUI(console)
    ui.banner()
    ui.begin(
        prompt,
        mode.value,
        session.id,
        [engine.models[model_id].model_name for model_id in model_ids],
    )
    event_sink = SQLiteEventSink(store)
    runtime_event = TaskEventAdapter(event_sink, task.id)
    def combined_event(kind, name, status, detail, error=None):
        ui.event(kind, name, status, detail, error)
        runtime_event(kind, name, status, detail, error)

    try:
        synthesis, verification, responses = asyncio.run(
            engine.run(task, model_ids, event_sink=combined_event)
        )
        store.save_run(task.id, responses, synthesis, verification)
        store.save_verification(verification)
        for response in responses:
            store.save_provider_usage(task.id, response)
        ui.finish(synthesis, verification.passed)
    except Exception as exc:  # noqa: BLE001
        ui.event("stage", "Runtime", "failed", "erro inesperado", str(exc))
        ui.finish(f"Rock encontrou um erro: {exc}", False)
        raise


@app.command("run")
def run(
    prompt: str = typer.Argument(...),
    mode: TaskMode = typer.Option(TaskMode.COUNCIL, "--mode", "-m"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated external agents for agent mode.",
    ),
) -> None:
    """Run a task through Rock's council."""
    selected = [x.strip() for x in agents.split(",")] if agents else None
    _run(prompt, mode, verbose, selected)


@app.command("ask")
def ask(
    prompt: str = typer.Argument(...),
    mode: TaskMode = typer.Option(TaskMode.COUNCIL, "--mode", "-m"),
    agents: str | None = typer.Option(None, "--agents"),
) -> None:
    """Alias for rock run."""
    selected = [x.strip() for x in agents.split(",")] if agents else None
    _run(prompt, mode, False, selected)


@app.command("agent-run")
def agent_run(
    prompt: str = typer.Argument(...),
    model: str | None = typer.Option(None, "--model"),
    iterations: int = typer.Option(1, "--iterations", min=1, max=16),
    skill: str | None = typer.Option(None, "--skill", help="Skill id to load from the registry."),
) -> None:
    """Run Rock's bounded internal model agent without tool execution."""
    configure_logging(False)
    settings = get_settings()
    engine, model_ids = build_engine()
    if not model_ids:
        raise typer.BadParameter(
            "No providers are configured. Use ROCK_MODE=mock or configure at least one API key."
        )

    selected = model_ids[0]
    if model:
        matches = [
            model_id
            for model_id in model_ids
            if model.lower() in {
                model_id.lower(),
                engine.models[model_id].provider.lower(),
                engine.models[model_id].model_name.lower(),
            }
        ]
        if not matches:
            raise typer.BadParameter(f"Model not found: {model}")
        selected = matches[0]

    task_id = str(uuid4())
    selected_model = engine.models[selected]
    registry = SkillRegistry(default_skill_roots())
    registry.discover()
    selected_skills = [skill] if skill and registry.get(skill) else []
    if skill and not selected_skills:
        raise typer.BadParameter(f"Skill not found: {skill}")
    agent = Agent(
        id=f"agent-{task_id}",
        name="Rock Agent",
        model=selected_model,
        system_policy=(
            "Work only with the supplied task and model context. "
            "Do not claim to have executed tools or changed the system."
        ),
        max_iterations=iterations,
        skills=selected_skills,
    )
    runtime = AgentRuntime(engine.providers, registry)
    result = asyncio.run(
        runtime.execute(
            agent,
            prompt,
            task_id=task_id,
            timeout=settings.rock_timeout_seconds,
        )
    )
    if result.final_response:
        console.print(
            Panel(
                result.final_response.content or result.final_response.error or "",
                title=f"Agent: {selected_model.model_name} [{result.status.value}]",
            )
        )
    if result.status.value != "success":
        raise typer.Exit(code=1)


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
def agents() -> None:
    """List external coding agents detected on this machine."""
    runner = ExternalAgentRunner()
    found = runner.available()
    if not found:
        console.print("No external agents detected.")
        return
    for agent in found:
        console.print(f"✓ {agent.name}: {agent.description}")


@app.command()
def agent(
    name: str = typer.Argument(...),
    prompt: str = typer.Argument(...),
    cwd: str | None = typer.Option(None, "--cwd"),
) -> None:
    """Run one installed external coding agent through Rock."""
    runner = ExternalAgentRunner()
    execution = asyncio.run(runner.run(name, prompt, task_id=str(uuid4()), cwd=cwd))
    console.print(Panel(execution.output.get("stdout", ""), title=f"Agent: {name}"))
    if execution.output.get("stderr"):
        console.print(execution.output["stderr"])
    if execution.error:
        raise typer.Exit(code=1)


@app.command()
def sessions() -> None:
    """Show stored session/task database location."""
    settings = get_settings()
    console.print(f"SQLite: {settings.rock_db_path}")


@app.command()
def doctor(
    check: bool = typer.Option(
        False,
        "--check",
        help="Make live provider checks. May consume API credits.",
    ),
) -> None:
    """Check local configuration; use --check for live provider connectivity."""
    get_settings.cache_clear()
    settings = get_settings()
    console.print(Panel.fit("ROCK DOCTOR"))
    console.print("✓ Python runtime detected")
    console.print(f"✓ Mode: {settings.rock_mode}")
    console.print(f"✓ SQLite: {settings.rock_db_path}")

    definitions = [
        ("OpenAI", settings.openai_api_key, settings.rock_openai_model),
        ("Anthropic", settings.anthropic_api_key, settings.rock_anthropic_model),
        ("DeepSeek", settings.deepseek_api_key, settings.rock_deepseek_model),
        ("Perplexity", settings.perplexity_api_key, settings.rock_perplexity_model),
        ("Gemini", settings.gemini_api_key, settings.rock_gemini_model),
    ]
    for name, key, model in definitions:
        status = "configured" if key else "not configured"
        console.print(f"{'✓' if key else '○'} {name}: {status} | model={model}")

    console.print(
        f"✓ Ollama: endpoint={settings.ollama_base_url} | model={settings.rock_ollama_model}"
    )

    if check:
        if settings.rock_mode.lower() == "mock":
            console.print("✓ Live check skipped: ROCK_MODE=mock")
        else:
            check_definitions = [
                ("openai", settings.rock_openai_model, settings.openai_api_key),
                ("anthropic", settings.rock_anthropic_model, settings.anthropic_api_key),
                ("deepseek", settings.rock_deepseek_model, settings.deepseek_api_key),
                ("perplexity", settings.rock_perplexity_model, settings.perplexity_api_key),
                ("gemini", settings.rock_gemini_model, settings.gemini_api_key),
            ]
            providers: dict[str, Provider] = {}
            models: dict[str, Model] = {}
            for provider_name, model_name, configured in check_definitions:
                if not configured:
                    continue
                providers[provider_name] = LiteLLMProvider(provider_name, api_key=configured)
                model_id = f"{provider_name}:doctor"
                models[model_id] = Model(
                    id=model_id,
                    provider=provider_name,
                    model_name=model_name,
                )

            if not models:
                console.print("✗ Live check unavailable: no configured online providers")
            else:
                async def check_providers() -> list[tuple[str, str, bool]]:
                    results = []
                    for model_id, model in models.items():
                        healthy = await providers[model.provider].health_check(model, timeout=10)
                        results.append((model.provider, model.model_name, healthy))
                    return results

                results = asyncio.run(check_providers())
                display_names = {
                    "openai": "OpenAI",
                    "anthropic": "Anthropic",
                    "deepseek": "DeepSeek",
                    "perplexity": "Perplexity",
                    "gemini": "Gemini",
                }
                for name, model, healthy in results:
                    display_name = display_names.get(name, name)
                    console.print(
                        f"{'✓' if healthy else '✗'} {display_name}: "
                        f"{'reachable' if healthy else 'unavailable'} | model={model}"
                    )
    else:
        console.print("[dim]Live provider checks disabled. Use: rock doctor --check[/dim]")

    runner = ExternalAgentRunner()
    available = runner.available()
    console.print(
        "✓ External agents: " + (", ".join(a.name for a in available) if available else "none")
    )
    console.print("✓ Skill roots:")
    for root in default_skill_roots():
        console.print(f"  - {root}")


@app.callback(
    invoke_without_command=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def root(ctx: typer.Context) -> None:
    get_settings.cache_clear()
    if ctx.invoked_subcommand is not None:
        return

    prompt = " ".join(ctx.args).strip()
    if prompt:
        _run(prompt, TaskMode.COUNCIL, False)
        return

    ui = RockTerminalUI(console)
    ui.banner()
    console.print("[dim]Digite /help para comandos ou /exit para sair.[/dim]")
    while True:
        prompt = interactive_prompt(console)
        if not prompt:
            continue
        if prompt in {"/exit", "/quit"}:
            break
        if prompt == "/help":
            console.print(ctx.get_help())
            continue
        _run(prompt, TaskMode.COUNCIL, False)
