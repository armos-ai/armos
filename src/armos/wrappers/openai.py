# SPDX-License-Identifier: MIT
from typing import Any, Literal
from ..guard import Armos, _DEFAULT_VAULT_TTL
from .base import _MaskingMixin, _StreamingDemasker, SYSTEM_HINT


class _ArmosOpenAIStream:
    """
    Wraps an OpenAI Stream[ChatCompletionChunk].
    Demaskes PII tokens in delta.content as chunks arrive, handling the case
    where a token is split across multiple chunks.
    """

    def __init__(self, stream: Any, demask_fn):
        self._stream = stream
        self._demasker = _StreamingDemasker(demask_fn)

    def __iter__(self):
        for chunk in self._stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                yield chunk
                continue

            choice = choices[0]
            delta = choice.delta
            content = getattr(delta, "content", None)
            finish_reason = getattr(choice, "finish_reason", None)

            output = ""
            if content:
                output = self._demasker.feed(content)
            if finish_reason:
                output += self._demasker.flush()

            if output:
                delta.content = output
                yield chunk
            elif finish_reason:
                yield chunk
            # else: buffering — skip empty chunk

    def __enter__(self):
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, *args):
        if hasattr(self._stream, "__exit__"):
            return self._stream.__exit__(*args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class ArmosCompletions(_MaskingMixin):
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
                    msgs[0] = {**msgs[0], "content": msgs[0]["content"] + "\n\n" + SYSTEM_HINT}
                else:
                    kwargs["messages"] = [{"role": "system", "content": SYSTEM_HINT}] + msgs

        response = self._completions.create(**kwargs)

        if kwargs.get("stream"):
            return _ArmosOpenAIStream(response, self._guard.demask)
        return self._demask_response(response)

    def _demask_response(self, response: Any) -> Any:
        if not hasattr(response, "choices"):
            return response
        for choice in response.choices:
            if hasattr(choice, "message") and choice.message and choice.message.content:
                choice.message.content = self._guard.demask(choice.message.content)
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


class ArmosResponses(_MaskingMixin):
    """Wraps openai.resources.responses.Responses. Intercepts create() only."""

    def __init__(self, responses: Any, guard: Armos):
        self._responses = responses
        self._guard = guard

    def create(self, **kwargs) -> Any:
        has_pii = False

        if "input" in kwargs:
            inp = kwargs["input"]
            if isinstance(inp, str):
                kwargs["input"], has_pii = self._mask_string(inp)
            elif isinstance(inp, list):
                kwargs["input"], has_pii = self._mask_messages(inp)

        if has_pii:
            existing = kwargs.get("instructions") or ""
            kwargs["instructions"] = (existing + "\n\n" + SYSTEM_HINT).strip() if existing else SYSTEM_HINT

        response = self._responses.create(**kwargs)
        return self._demask_response(response)

    def _demask_response(self, response: Any) -> Any:
        if not hasattr(response, "output"):
            return response
        for item in response.output:
            if hasattr(item, "content") and isinstance(item.content, list):
                for block in item.content:
                    if hasattr(block, "text") and block.text:
                        block.text = self._guard.demask(block.text)
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._responses, name)


class ArmosEmbeddings(_MaskingMixin):
    """Wraps openai.resources.embeddings.Embeddings. Masks input text before sending."""

    def __init__(self, embeddings: Any, guard: Armos):
        self._embeddings = embeddings
        self._guard = guard

    def create(self, **kwargs) -> Any:
        if "input" in kwargs:
            inp = kwargs["input"]
            if isinstance(inp, str):
                kwargs["input"], _ = self._mask_string(inp)
            elif isinstance(inp, list):
                kwargs["input"], _ = self._mask_input_list(inp)

        return self._embeddings.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._embeddings, name)


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
        self.responses = ArmosResponses(client.responses, self._guard)
        self.embeddings = ArmosEmbeddings(client.embeddings, self._guard)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
