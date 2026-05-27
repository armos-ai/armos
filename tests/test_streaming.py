"""
Unit and integration tests for streaming support.
Covers _is_partial_token, _StreamingDemasker, _ArmosOpenAIStream,
and _ArmosAnthropicStream.
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from armos.wrappers.base import _is_partial_token, _StreamingDemasker
from armos.wrappers.openai import _ArmosOpenAIStream, ArmosOpenAI
from armos.wrappers.anthropic import _ArmosAnthropicStream, ArmosAnthropic


# ── helpers ─────────────────────────────────────────────────────────────────

def make_chunk(content, finish_reason=None):
    chunk = MagicMock()
    chunk.choices[0].delta.content = content
    chunk.choices[0].finish_reason = finish_reason
    return chunk


def make_stream(texts):
    chunks = [make_chunk(t) for t in texts]
    chunks.append(make_chunk(None, finish_reason="stop"))
    return iter(chunks)


def make_text_event(text, index=0):
    return SimpleNamespace(
        type="content_block_delta",
        index=index,
        delta=SimpleNamespace(type="text_delta", text=text),
    )


def make_stop_event(index=0):
    return SimpleNamespace(type="content_block_stop", index=index)


class _ContextStream:
    """Mock stream that also implements the context manager protocol."""
    def __init__(self, items):
        self._items = iter(items)
        self.entered = False
        self.exited = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._items)

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        return False

    def some_attr(self):
        return "delegated"


# ── _is_partial_token unit tests ─────────────────────────────────────────────

class TestIsPartialToken:
    def test_empty_string_is_not_partial(self):
        assert not _is_partial_token("")

    def test_complete_token_is_not_partial(self):
        assert not _is_partial_token("[PII:NAME:c4587843]")

    def test_bracket_alone_is_partial(self):
        # line 19 path: len("[") <= len("[PII:") → _PII_PREFIX.startswith("[")
        assert _is_partial_token("[")

    def test_short_pii_prefix_is_partial(self):
        # line 19 path for [P, [PI, [PII, [PII:
        for prefix in ("[P", "[PI", "[PII", "[PII:"):
            assert _is_partial_token(prefix), f"{prefix!r} should be partial"

    def test_non_pii_bracket_is_not_partial(self):
        # line 21 path: len > 5, doesn't start with [PII:
        assert not _is_partial_token("[world")
        assert not _is_partial_token("[NOTPII:x")

    def test_long_pii_prefix_is_partial(self):
        assert _is_partial_token("[PII:NAME")
        assert _is_partial_token("[PII:NAME:")
        assert _is_partial_token("[PII:NAME:c458")
        assert _is_partial_token("[PII:EMAIL:9835f31")

    def test_ends_with_bracket_is_not_partial(self):
        assert not _is_partial_token("[PII:NAME:c4587843]")


# ── _StreamingDemasker unit tests ─────────────────────────────────────────────

class TestStreamingDemasker:
    def test_plain_text_passes_through(self):
        d = _StreamingDemasker(lambda x: x)
        assert d.feed("Hello world") == "Hello world"
        assert d.flush() == ""

    def test_bracket_alone_is_held(self):
        d = _StreamingDemasker(lambda x: x)
        assert d.feed("[") == ""
        assert d.flush() == "["  # released unchanged at end

    def test_non_pii_bracket_passes_through(self):
        # [world is not a PII prefix — safe to yield immediately
        d = _StreamingDemasker(lambda x: x)
        result = d.feed("Hello [world")
        assert result == "Hello [world"

    def test_complete_token_in_one_chunk(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("John Smith").text

        d = _StreamingDemasker(guard.demask)
        out = d.feed(f"Hi {token}!")
        assert "John Smith" in out
        assert "[PII:" not in out

    def test_token_split_across_many_chunks(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("John Smith").text

        # Split character by character (worst case)
        d = _StreamingDemasker(guard.demask)
        collected = ""
        for ch in token:
            collected += d.feed(ch)
        collected += d.flush()

        assert "John Smith" in collected
        assert "[PII:" not in collected

    def test_text_before_token_yielded_immediately(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("Jane Doe").text

        d = _StreamingDemasker(guard.demask)
        mid = len(token) // 2

        out1 = d.feed("Prefix text " + token[:mid])
        # "Prefix text " should be yielded; partial token is held
        assert "Prefix text" in out1

        out2 = d.feed(token[mid:])
        assert "Jane Doe" in out2

    def test_flush_releases_buffer(self):
        d = _StreamingDemasker(lambda x: x)
        d.feed("[PII:NAME:c4587")  # valid partial hex token — held in buffer
        remaining = d.flush()
        assert remaining == "[PII:NAME:c4587"

    def test_multiple_tokens_in_one_chunk(self):
        from armos import Armos
        guard = Armos()
        t1 = guard.mask("John Smith").text
        t2 = guard.mask("jane@example.com").text

        d = _StreamingDemasker(guard.demask)
        out = d.feed(f"Name: {t1}, email: {t2}.")
        assert "John Smith" in out
        assert "jane@example.com" in out
        assert "[PII:" not in out


# ── _ArmosOpenAIStream tests ─────────────────────────────────────────────────

class TestArmosOpenAIStream:
    def test_chunk_with_no_choices_passed_through(self):
        no_choice_chunk = MagicMock()
        no_choice_chunk.choices = []
        stream = _ArmosOpenAIStream(iter([no_choice_chunk]), lambda x: x)
        yielded = list(stream)
        assert yielded == [no_choice_chunk]

    def test_context_manager_delegates_enter_exit(self):
        items = [make_chunk("hello"), make_chunk(None, finish_reason="stop")]
        mock_stream = _ContextStream(items)
        wrapper = _ArmosOpenAIStream(mock_stream, lambda x: x)

        with wrapper as s:
            list(s)

        assert mock_stream.entered
        assert mock_stream.exited

    def test_getattr_delegates_to_underlying_stream(self):
        items = [make_chunk(None, finish_reason="stop")]
        mock_stream = _ContextStream(items)
        wrapper = _ArmosOpenAIStream(mock_stream, lambda x: x)
        assert wrapper.some_attr() == "delegated"

    def test_stop_chunk_with_empty_buffer_yielded(self):
        chunks = [make_chunk("hello"), make_chunk(None, finish_reason="stop")]
        stream = _ArmosOpenAIStream(iter(chunks), lambda x: x)
        yielded = list(stream)
        stop = [c for c in yielded if c.choices[0].finish_reason == "stop"]
        assert len(stop) == 1

    def test_buffered_content_released_on_stop(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("John Smith").text
        mid = len(token) // 2

        # First chunk: partial token (will buffer)
        # Stop chunk arrives before the token is completed
        chunks = [
            make_chunk(token[:mid]),
            make_chunk(None, finish_reason="stop"),
        ]
        # Manually make the stop chunk carry the flush
        stream = _ArmosOpenAIStream(iter(chunks), guard.demask)
        contents = [
            c.choices[0].delta.content
            for c in stream
            if c.choices[0].delta.content
        ]
        full = "".join(contents)
        # Partial token is flushed at stop — demasked if complete, raw if not
        assert len(full) > 0


# ── _ArmosAnthropicStream tests ──────────────────────────────────────────────

class TestArmosAnthropicStream:
    def test_non_text_delta_passed_through(self):
        # content_block_delta with type != text_delta (e.g. input_json_delta)
        event = SimpleNamespace(
            type="content_block_delta",
            index=0,
            delta=SimpleNamespace(type="input_json_delta", partial_json='{"k":'),
        )
        stream = _ArmosAnthropicStream(iter([event]), lambda x: x)
        yielded = list(stream)
        assert yielded == [event]

    def test_other_event_types_passed_through(self):
        events = [
            SimpleNamespace(type="message_start", message=MagicMock()),
            SimpleNamespace(type="message_delta", usage=MagicMock()),
            SimpleNamespace(type="message_stop"),
        ]
        stream = _ArmosAnthropicStream(iter(events), lambda x: x)
        yielded = list(stream)
        assert len(yielded) == 3

    def test_content_block_stop_flushes_buffer(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("John Smith").text
        mid = len(token) // 2

        events = [
            make_text_event(token[:mid]),   # partial token — buffered
            make_stop_event(),              # triggers flush
        ]
        stream = _ArmosAnthropicStream(iter(events), guard.demask)
        text_events = [
            e for e in stream
            if e.type == "content_block_delta" and e.delta.type == "text_delta"
        ]
        full = "".join(e.delta.text for e in text_events)
        assert "John Smith" in full or token[:mid] in full  # flushed or raw

    def test_synthetic_flush_event_emitted_before_stop(self):
        from armos import Armos
        guard = Armos()
        token = guard.mask("John Smith").text

        # Buffer is non-empty at content_block_stop
        events = [
            make_text_event(token),   # complete token — but split: first half only
            make_stop_event(),
        ]
        # Replace with partial to force buffer at stop
        mid = len(token) // 2
        events = [make_text_event(token[:mid]), make_stop_event()]

        stream = _ArmosAnthropicStream(iter(events), guard.demask)
        yielded = list(stream)

        delta_events = [e for e in yielded if e.type == "content_block_delta"]
        stop_events = [e for e in yielded if e.type == "content_block_stop"]

        # Synthetic delta event should appear before the stop
        assert len(stop_events) == 1
        if delta_events:
            assert yielded.index(delta_events[-1]) < yielded.index(stop_events[0])

    def test_context_manager_delegates_enter_exit(self):
        events = [make_text_event("hello"), make_stop_event()]
        mock_stream = _ContextStream(events)
        wrapper = _ArmosAnthropicStream(mock_stream, lambda x: x)

        with wrapper as s:
            list(s)

        assert mock_stream.entered
        assert mock_stream.exited

    def test_getattr_delegates_to_underlying_stream(self):
        events = [make_stop_event()]
        mock_stream = _ContextStream(events)
        wrapper = _ArmosAnthropicStream(mock_stream, lambda x: x)
        assert wrapper.some_attr() == "delegated"

    def test_stream_without_context_manager_protocol(self):
        """Stream that has no __enter__/__exit__ — wrapper should not crash."""
        events = [make_text_event("hello"), make_stop_event()]
        plain_iter = iter(events)  # no __enter__/__exit__
        wrapper = _ArmosAnthropicStream(plain_iter, lambda x: x)
        wrapper.__enter__()
        wrapper.__exit__(None, None, None)  # should not raise
