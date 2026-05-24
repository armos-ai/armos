# SPDX-License-Identifier: MIT
from typing import Any, Literal
from ..guard import Armos, _DEFAULT_VAULT_TTL
from .base import _MaskingMixin, SYSTEM_HINT


class ArmosMessages(_MaskingMixin):
    """Wraps anthropic.resources.Messages. Intercepts create() only."""

    def __init__(self, messages: Any, guard: Armos):
        self._messages = messages
        self._guard = guard

    def create(self, **kwargs) -> Any:
        has_pii = False
        if "messages" in kwargs:
            kwargs["messages"], has_pii = self._mask_messages(kwargs["messages"])

        if has_pii:
            existing = kwargs.get("system") or ""
            kwargs["system"] = (existing + "\n\n" + SYSTEM_HINT).strip() if existing else SYSTEM_HINT

        response = self._messages.create(**kwargs)
        return self._demask_response(response)

    def _demask_response(self, response: Any) -> Any:
        if not hasattr(response, "content"):
            return response
        for block in response.content:
            if hasattr(block, "text") and block.text:
                block.text = self._guard.demask(block.text)
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)


class ArmosAnthropic:
    """
    Drop-in replacement for anthropic.Anthropic.
    Masks PII in prompts before sending to Anthropic.
    Restores real values in responses.

    Usage:
        from anthropic import Anthropic
        from armos import ArmosAnthropic
        client = ArmosAnthropic(Anthropic())
    """

    def __init__(
        self,
        client: Any,
        store: Literal["redis"] | None = None,
        redis_url: str | None = None,
        vault_ttl: int = _DEFAULT_VAULT_TTL,
    ):
        self._client = client
        self._guard = Armos(store=store, redis_url=redis_url, vault_ttl=vault_ttl)
        self.messages = ArmosMessages(client.messages, self._guard)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
