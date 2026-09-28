from rock.core.contracts import Capability, Model, Response
from rock.core.providers import Provider


class MockProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name

    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        return Response(
            provider=self.name,
            model=model.model_name,
            content=(
                f"Mock response from {self.name}. "
                f"Received task: {prompt}"
            ),
        )

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT, Capability.STRUCTURED_OUTPUT}
