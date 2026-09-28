# ruff: isort: skip_file
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


WOLF = r"""           /\__
      ____/  _  \\__
     /    \/ \\     `-.
    /  /\  \\_/  _     >
   /__/  \\______/ \\___/
      \\   ROCK   /
       \\_______/"""


@dataclass
class Activity:
    name: str
    kind: str
    status: str = "pending"
    detail: str = "aguardando"
    started: float | None = None
    finished: float | None = None
    error: str | None = None

    @property
    def elapsed(self) -> str:
        if self.started is None:
            return "—"
        end = self.finished if self.finished is not None else monotonic()
        return f"{end - self.started:.1f}s"


@dataclass
class TerminalState:
    prompt: str = ""
    mode: str = "council"
    session_id: str = ""
    models: dict[str, Activity] = field(default_factory=dict)
    stages: dict[str, Activity] = field(default_factory=dict)
    phase: str = "preparing"
    final_status: str = "running"
    final_text: str = ""


class RockTerminalUI:
    """Live terminal UI for Rock's real execution events."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.state = TerminalState()
        self._live: Live | None = None

    def banner(self) -> None:
        title = Text()
        title.append(WOLF + "\n", style="bold cyan")
        title.append("ROCK", style="bold white")
        title.append("  Multi-Model Agent Runtime\n", style="bold cyan")
        title.append("     Think together. Build better.", style="dim")
        self.console.print(Panel(title, border_style="cyan", padding=(0, 2)))

    def begin(self, prompt: str, mode: str, session_id: str, model_names: list[str]) -> None:
        self.state = TerminalState(
            prompt=prompt,
            mode=mode,
            session_id=session_id[:8],
            models={name: Activity(name=name, kind="model") for name in model_names},
            stages={
                "Critic": Activity("Critic", "stage"),
                "Synthesizer": Activity("Synthesizer", "stage"),
                "Verifier": Activity("Verifier", "stage"),
            },
        )
        self._live = Live(
            self.render(),
            console=self.console,
            refresh_per_second=8,
            transient=False,
        )
        self._live.start()

    def event(
        self,
        kind: str,
        name: str,
        status: str,
        detail: str,
        error: str | None = None,
    ) -> None:
        collection = self.state.models if kind == "model" else self.state.stages
        activity = collection.setdefault(name, Activity(name=name, kind=kind))
        activity.status = status
        activity.detail = detail
        activity.error = error
        if status == "running" and activity.started is None:
            activity.started = monotonic()
        if status in {"success", "failed", "timeout", "cancelled"}:
            if activity.started is None:
                activity.started = monotonic()
            activity.finished = monotonic()

        if kind == "stage" and status == "running":
            self.state.phase = name.lower()
        elif kind == "model" and status == "running":
            self.state.phase = "models"

        if self._live:
            self._live.update(self.render(), refresh=True)

    def finish(self, final_text: str, passed: bool) -> None:
        self.state.final_text = final_text
        self.state.final_status = "success" if passed else "failed"
        self.state.phase = "complete"
        if self._live:
            self._live.update(self.render(), refresh=True)
            self._live.stop()
            self._live = None

    @staticmethod
    def _status(status: str) -> tuple[str, str]:
        return {
            "pending": ("○", "dim"),
            "running": ("◉", "yellow"),
            "success": ("✓", "green"),
            "failed": ("✗", "red"),
            "timeout": ("!", "red"),
            "cancelled": ("×", "magenta"),
        }.get(status, ("•", "white"))

    def _activity_table(self, title: str, items: dict[str, Activity]) -> Table:
        table = Table(
            title=title,
            title_style="bold cyan",
            box=None,
            expand=True,
            padding=(0, 1),
        )
        table.add_column("Estado", width=3, justify="center")
        table.add_column("Nome", style="white")
        table.add_column("Status")
        table.add_column("Tempo", justify="right", style="dim")
        for activity in items.values():
            icon, style = self._status(activity.status)
            status = Text(activity.detail, style=style)
            if activity.error:
                status.append(f" — {activity.error}", style="red")
            table.add_row(icon, activity.name, status, activity.elapsed)
        return table

    def render(self) -> Group:
        width = self.console.size.width
        prompt_panel = Panel(
            Text(f"> {self.state.prompt}", style="white"),
            title="Você",
            border_style="cyan",
            padding=(0, 1),
        )
        models = self._activity_table("1. MODELOS", self.state.models)
        stages = self._activity_table("2. ROCK COUNCIL", self.state.stages)

        info = Table(box=None, expand=True, padding=(0, 1))
        info.add_column("Campo", style="dim")
        info.add_column("Valor", justify="right")
        info.add_row("Modo", self.state.mode)
        info.add_row("Sessão", self.state.session_id or "—")
        info.add_row(
            "Modelos",
            f"{sum(a.status == 'success' for a in self.state.models.values())}/"
            f"{len(self.state.models)}",
        )
        info.add_row(
            "Etapas",
            f"{sum(a.status == 'success' for a in self.state.stages.values())}/"
            f"{len(self.state.stages)}",
        )

        status_text = "Processando..."
        border = "yellow"
        if self.state.final_status == "success":
            status_text = "✓ Processo concluído"
            border = "green"
        elif self.state.final_status == "failed":
            status_text = "✗ Processo concluído com falhas"
            border = "red"

        final = Panel(
            Group(
                Text(status_text, style=f"bold {border}"),
                Text(self.state.final_text or "Aguardando resposta final...", style="white"),
            ),
            title="ROCK",
            border_style=border,
            padding=(0, 1),
        )

        if width < 100:
            body = Group(
                prompt_panel,
                models,
                stages,
                Panel(info, title="Status", border_style="blue"),
                final,
            )
        else:
            from rich.columns import Columns

            body = Group(
                prompt_panel,
                Columns(
                    [Group(models, stages, final), Panel(info, title="Execução", border_style="blue")],
                    equal=False,
                    expand=True,
                ),
            )
        return body

    def close(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None


def interactive_prompt(console: Console) -> str:
    from rich.prompt import Prompt

    return Prompt.ask("[bold cyan]rock>[/bold cyan]").strip()
