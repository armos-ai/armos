# SPDX-License-Identifier: MIT
import re
from typing import Any, Callable, List

SYSTEM_HINT = "Reproduce any [PII:TYPE:HASH] tokens in your response exactly as written."

_PII_PREFIX = "[PII:"


def _is_partial_token(s: str) -> bool:
    """
    Return True if s is an incomplete prefix of a [PII:TYPE:HASH] token.
    Handles the case where the LLM streams the token character-by-character,
    e.g. '[', '[P', '[PI', '[PII:', '[PII:NAME', '[PII:NAME:c458'.
    """
    if not s or s.endswith("]"):
        return False
    if len(s) <= len(_PII_PREFIX):
        return _PII_PREFIX.startswith(s)
    if not s.startswith(_PII_PREFIX):
        return False
    rest = s[len(_PII_PREFIX):]
    return bool(re.match(r"^[A-Z]*:?[a-f0-9]{0,8}$", rest))


class _StreamingDemasker:
    """
    Buffers streaming text chunks and demaskes complete PII tokens as they arrive.

    A token like [PII:NAME:c4587843] may arrive split across many chunks
    (e.g. '[', 'PI', 'I', ':', 'NAME', ':c', '458', '784', '3', ']').
    This class holds back text from the point a potential token prefix appears
    until the closing ] arrives, then releases the fully demasked text.
    """

    def __init__(self, demask_fn: Callable[[str], str]):
        self._demask = demask_fn
        self._buffer = ""

    def feed(self, text: str) -> str:
        """Feed one chunk. Returns safe-to-yield demasked text (empty if still buffering)."""
        self._buffer += text
        return self._flush_safe()

    def flush(self) -> str:
        """End of stream — release everything remaining (partial tokens left as-is)."""
        result = self._demask(self._buffer)
        self._buffer = ""
        return result

    def _flush_safe(self) -> str:
        buf = self._buffer
        last_bracket = buf.rfind("[")
        if last_bracket == -1:
            self._buffer = ""
            return self._demask(buf)
        tail = buf[last_bracket:]
        if _is_partial_token(tail):
            # Hold the partial prefix, yield everything before it
            self._buffer = tail
            safe = buf[:last_bracket]
            return self._demask(safe) if safe else ""
        # [ is present but it's a complete token or a non-PII bracket — safe to flush all
        self._buffer = ""
        return self._demask(buf)


class _MaskingMixin:
    """
    Common masking utilities shared across all SDK wrappers.

    Subclasses must set self._guard (an Armos instance) before calling any method.
    """

    def _mask_string(self, text: str) -> tuple:
        """Mask a single string. Returns (masked_text, has_pii)."""
        if self._guard._tokenizer.contains_tokens(text):
            return text, False
        result = self._guard.mask(text)
        return (result.text, True) if result.has_pii else (text, False)

    def _mask_messages(self, messages: List[dict]) -> tuple:
        """
        Mask PII in a list of message dicts.
        Handles both string content and content block lists.
        Returns (masked_messages, has_pii).
        """
        masked = []
        any_pii = False
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                masked_text, pii = self._mask_string(content)
                if pii:
                    any_pii = True
                    msg = {**msg, "content": masked_text}
            elif isinstance(content, list):
                masked_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        masked_text, pii = self._mask_string(text)
                        if pii:
                            any_pii = True
                            block = {**block, "text": masked_text}
                    masked_blocks.append(block)
                msg = {**msg, "content": masked_blocks}
            masked.append(msg)
        return masked, any_pii

    def _mask_input_list(self, items: list) -> tuple:
        """
        Mask a list of strings (e.g. embeddings input).
        Returns (masked_items, has_pii).
        """
        masked = []
        any_pii = False
        for item in items:
            if isinstance(item, str):
                masked_text, pii = self._mask_string(item)
                if pii:
                    any_pii = True
                masked.append(masked_text)
            else:
                masked.append(item)
        return masked, any_pii


class _AsyncMaskingMixin:
    """
    Async counterpart to _MaskingMixin.

    Subclasses must set self._guard (an Armos instance) before calling any method.
    mask() delegates to guard.amask() which runs spaCy in a thread pool.
    demask() is called synchronously — it's pure regex + dict lookup, fast enough.
    """

    async def _mask_string_async(self, text: str) -> tuple:
        if self._guard._tokenizer.contains_tokens(text):
            return text, False
        result = await self._guard.amask(text)
        return (result.text, True) if result.has_pii else (text, False)

    async def _mask_messages_async(self, messages: List[dict]) -> tuple:
        masked = []
        any_pii = False
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                masked_text, pii = await self._mask_string_async(content)
                if pii:
                    any_pii = True
                    msg = {**msg, "content": masked_text}
            elif isinstance(content, list):
                masked_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        masked_text, pii = await self._mask_string_async(text)
                        if pii:
                            any_pii = True
                            block = {**block, "text": masked_text}
                    masked_blocks.append(block)
                msg = {**msg, "content": masked_blocks}
            masked.append(msg)
        return masked, any_pii

    async def _mask_input_list_async(self, items: list) -> tuple:
        masked = []
        any_pii = False
        for item in items:
            if isinstance(item, str):
                masked_text, pii = await self._mask_string_async(item)
                if pii:
                    any_pii = True
                masked.append(masked_text)
            else:
                masked.append(item)
        return masked, any_pii


class _ArmosOpenAIAsyncStream:
    """
    Wraps an OpenAI AsyncStream[ChatCompletionChunk].
    Async counterpart to _ArmosOpenAIStream.
    """

    def __init__(self, stream: Any, demask_fn: Callable[[str], str]):
        self._stream = stream
        self._demasker = _StreamingDemasker(demask_fn)

    async def __aiter__(self):
        async for chunk in self._stream:
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

    async def __aenter__(self):
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, *args):
        if hasattr(self._stream, "__aexit__"):
            return await self._stream.__aexit__(*args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _ArmosAnthropicAsyncStream:
    """
    Wraps an Anthropic AsyncStream[MessageStreamEvent].
    Async counterpart to _ArmosAnthropicStream.
    """

    def __init__(self, stream: Any, demask_fn: Callable[[str], str]):
        self._stream = stream
        self._demasker = _StreamingDemasker(demask_fn)

    async def __aiter__(self):
        from types import SimpleNamespace
        async for event in self._stream:
            event_type = getattr(event, "type", None)

            if event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                if delta and getattr(delta, "type", None) == "text_delta":
                    text = getattr(delta, "text", "") or ""
                    safe = self._demasker.feed(text)
                    if safe:
                        delta.text = safe
                        yield event
                else:
                    yield event

            elif event_type == "content_block_stop":
                remaining = self._demasker.flush()
                if remaining:
                    yield SimpleNamespace(
                        type="content_block_delta",
                        index=getattr(event, "index", 0),
                        delta=SimpleNamespace(type="text_delta", text=remaining),
                    )
                yield event

            else:
                yield event

    async def __aenter__(self):
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, *args):
        if hasattr(self._stream, "__aexit__"):
            return await self._stream.__aexit__(*args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)
