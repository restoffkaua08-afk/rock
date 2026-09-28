from rock.core.contracts import Capability, Model, Response
from rock.core.providers import Provider


class MockProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name

    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        if "debate judge" in prompt.lower():
            content = "Mock judge: the debate findings are internally consistent."
        elif "adjudication agent" in prompt.lower():
            content = "INCONCLUSIVE\nMock adjudicator cannot establish which claim is correct from the supplied evidence.\nConfidence: 0.4"
        elif "verification agent" in prompt.lower():
            content = "PASS\nMock verification: synthesis is consistent with the supplied responses."
        elif "critical reviewer" in prompt.lower():
            content = "Mock critique: responses are available and internally consistent."
        elif "synthesis agent" in prompt.lower():
            content = f"Mock synthesis from {self.name}. The supplied responses were considered. Mock response material was incorporated."
        else:
            content = f"Mock response from {self.name}. Received task: {prompt}"

        return Response(
            provider=self.name,
            model=model.model_name,
            content=content,
        )

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT, Capability.STRUCTURED_OUTPUT}
