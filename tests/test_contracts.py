from rock.core.contracts import Capability, Task, TaskMode


def test_task_defaults() -> None:
    task = Task(id="t1", prompt="hello")
    assert task.mode == TaskMode.COUNCIL
    assert Capability.TEXT in task.requested_capabilities
