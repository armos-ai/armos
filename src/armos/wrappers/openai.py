# SPDX-License-Identifier: MIT
from typing import Any, List, Literal
from ..guard import Armos, _DEFAULT_VAULT_TTL

_ARMOS_SYSTEM_HINT = "Reproduce any [PII:TYPE:HASH] tokens in your response exactly as written."


class ArmosCompletions:
    """Wraps openai.resources.chat.completions.Completions. Intercepts create() only."""

    def __init__(self, completions: Any, guard: Armos):
        self._completions = completions
        self._guard = guard

    def create(self, **kwargs) -> Any:
        if "messages" in kwargs:
            kwargs["messages"], has_pii = self._mask_messages(kwargs["messages"])
            if has_pii:
                msgs = kwargs["messages"]
                if msgs and msgs[0].get("role") == "system":
                    msgs[0] = {**msgs[0], "content": msgs[0]["content"] + "\n\n" + _ARMOS_SYSTEM_HINT}
                else:
                    kwargs["messages"] = [{"role": "system", "content": _ARMOS_SYSTEM_HINT}] + msgs

        response = self._completions.create(**kwargs)
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
                masked_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        if not self._guard._tokenizer.contains_tokens(text):
                            result = self._guard.mask(text)
                            if result.has_pii:
                                any_pii = True
                                part = {**part, "text": result.text}
                    masked_parts.append(part)
                msg = {**msg, "content": masked_parts}

            masked.append(msg)
        return masked, any_pii

    def _demask_response(self, response: Any) -> Any:
        if not hasattr(response, "choices"):
            return response
        for choice in response.choices:
            if hasattr(choice, "message") and choice.message:
                if choice.message.content:
                    choice.message.content = self._guard.demask(
                        choice.message.content
                    )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


class ArmosChat:
    """Wraps openai.resources.chat.Chat."""

    def __init__(self, chat: Any, guard: Armos):
        self._chat = chat
        self.completions = ArmosCompletions(chat.completions, guard)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class ArmosOpenAI:
    """
    Drop-in replacement for openai.OpenAI.
    Masks PII in prompts before sending to OpenAI.
    Restores real values in responses.

    Usage:
        from openai import OpenAI
        from armos import ArmosOpenAI
        client = ArmosOpenAI(OpenAI())

    All other OpenAI SDK methods pass through via __getattr__.
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
        self.chat = ArmosChat(client.chat, self._guard)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
