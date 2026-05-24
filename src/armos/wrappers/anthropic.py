# SPDX-License-Identifier: MIT
from typing import Any, List, Literal
from ..guard import Armos, _DEFAULT_VAULT_TTL

_ARMOS_SYSTEM_HINT = "Reproduce any [PII:TYPE:HASH] tokens in your response exactly as written."


class ArmosMessages:
    """Wraps anthropic.resources.Messages. Intercepts create() only."""

    def __init__(self, messages: Any, guard: Armos):
        self._messages = messages
        self._guard = guard

    def create(self, **kwargs) -> Any:
        has_pii = False
        if "messages" in kwargs:
            kwargs["messages"], has_pii = self._mask_messages(kwargs["messages"])

        if has_pii:
            existing_system = kwargs.get("system") or ""
            kwargs["system"] = (existing_system + "\n\n" + _ARMOS_SYSTEM_HINT).strip() if existing_system else _ARMOS_SYSTEM_HINT

        response = self._messages.create(**kwargs)
        return self._demask_response(response)

    def _mask_messages(self, messages: List[dict]) -> tuple:
        masked = []
        any_pii = False
        for msg in messages:
            content = msg.get("content")

            if isinstance(content, str):
                if not self._guard._tokenizer.contains_tokens(content):
                    result = self._guard.mask(content)
                    if result.has_pii:
                        any_pii = True
                        msg = {**msg, "content": result.text}

            elif isinstance(content, list):
                masked_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if not self._guard._tokenizer.contains_tokens(text):
                            result = self._guard.mask(text)
                            if result.has_pii:
                                any_pii = True
                                block = {**block, "text": result.text}
                    masked_blocks.append(block)
                msg = {**msg, "content": masked_blocks}

            masked.append(msg)
        return masked, any_pii

    def _demask_response(self, response: Any) -> Any:
        """Demask Anthropic response content blocks."""
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
