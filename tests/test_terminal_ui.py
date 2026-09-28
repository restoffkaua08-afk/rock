from rich.console import Console

from rock.cli.terminal_ui import RockTerminalUI


def test_terminal_ui_tracks_events() -> None:
    console = Console(record=True, width=120)
    ui = RockTerminalUI(console)
    ui.begin("hello", "council", "session-123", ["model-a", "model-b"])

    ui.event("model", "model-a", "running", "tentativa 1/1")
    ui.event("model", "model-a", "success", "concluído")
    ui.event("stage", "Critic", "running", "tentativa 1/1")
    ui.event("stage", "Critic", "success", "concluído")
    ui.finish("final answer", True)

    assert ui.state.models["model-a"].status == "success"
    assert ui.state.stages["Critic"].status == "success"
    assert ui.state.final_status == "success"
    assert ui.state.final_text == "final answer"
    assert ui._live is None
