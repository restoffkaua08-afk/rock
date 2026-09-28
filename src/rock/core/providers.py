from __future__ import annotations

from abc import ABC, abstractmethod

from rock.core.contracts import Capability, Model, Response


class Provider(ABC):
    """Rock-owned provider contract. Concrete providers are adapters."""

    @abstractmethod
    async def generate(self, prompt: str, model: Model, *, timeout: float) -> Response:
        raise NotImplementedError

    async def health_check(self, model: Model, *, timeout: float = 10) -> bool:
        try:
            response = await self.generate("ping", model, timeout=timeout)
            return not bool(response.error) and bool(response.content.strip())
        except Exception:
            return False

    def capabilities(self) -> set[Capability]:
        return {Capability.TEXT}

    async def cancel(self) -> None:
        return None
