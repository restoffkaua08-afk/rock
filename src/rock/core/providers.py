from __future__ import annotations

from abc import ABC, abstractmethod

from rock.core.contracts import Capability, Model, Response


class Provider(ABC):
    """Rock-owned provider contract. Concrete providers are adapters."""

    @abstractmethod
    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT}

    async def cancel(self) -> None:
        return None
