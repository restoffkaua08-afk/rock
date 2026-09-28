from rock.core.agent import AgentRuntime
from rock.core.contracts import Agent, Capability, ExecutionStatus, Model
from rock.providers.mock import MockProvider


async def test_agent_runtime_runs_bounded_turns() -> None:
    provider = MockProvider("mock")
    model = Model(
        id="mock:default",
        provider="mock",
        model_name="mock-model",
        capabilities={Capability.TEXT},
    )
    agent = Agent(
        id="agent-1",
        name="Researcher",
        model=model,
        system_policy="Be precise.",
        skills=["research"],
        max_iterations=2,
    )

    runtime = AgentRuntime({"mock": provider})
    result = await runtime.execute(
        agent,
        "Compare two approaches.",
        task_id="task-1",
        timeout=10,
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.iterations == 2
    assert result.final_response is not None
    assert len(result.responses) == 2


async def test_agent_runtime_rejects_missing_model() -> None:
    agent = Agent(id="agent-2", name="Empty")
    result = await AgentRuntime({}).execute(
        agent,
        "hello",
        task_id="task-2",
        timeout=10,
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.metadata["error"] == "agent has no model"
