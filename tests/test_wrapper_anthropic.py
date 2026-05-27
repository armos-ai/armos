import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from armos.wrappers.anthropic import ArmosAnthropic


def make_anthropic_text_event(text, index=0):
    return SimpleNamespace(
        type="content_block_delta",
        index=index,
        delta=SimpleNamespace(type="text_delta", text=text),
    )


def make_anthropic_stop_event(index=0):
    return SimpleNamespace(type="content_block_stop", index=index)


def make_mock_stream(texts):
    events = [make_anthropic_text_event(t) for t in texts]
    events.append(make_anthropic_stop_event())
    return iter(events)


def make_mock_anthropic_response(content: str):
    response = MagicMock()
    block = MagicMock()
    block.text = content
    response.content = [block]
    return response


def make_mock_client(response_content: str):
    client = MagicMock()
    client.messages.create.return_value = make_mock_anthropic_response(response_content)
    return client


def test_masks_pii_before_sending():
    client = make_mock_client("Here is a summary.")
    armos_client = ArmosAnthropic(client)

    armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": "Patient John Smith, Aadhaar 2345 6789 0123"}]
    )

    call_kwargs = client.messages.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "John Smith" not in sent_content
    assert "2345 6789 0123" not in sent_content
    assert "[PII:" in sent_content


def test_passthrough_non_message_methods():
    client = make_mock_client("ok")
    armos_client = ArmosAnthropic(client)
    armos_client.models.list()
    client.models.list.assert_called_once()


def test_no_double_masking():
    client = make_mock_client("ok")
    armos_client = ArmosAnthropic(client)

    already_masked = "Hello [PII:NAME:a1b2c3d4] how are you"
    armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": already_masked}]
    )

    call_kwargs = client.messages.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert sent_content.count("[PII:NAME:a1b2c3d4]") == 1


def test_system_hint_injected_only_when_pii_detected():
    """System hint must be added when PII is found, absent when message is clean."""
    client = make_mock_client("ok")
    armos_client = ArmosAnthropic(client)

    # PII message — hint should appear
    armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": "Patient John Smith, Aadhaar 2345 6789 0123"}]
    )
    call_kwargs = client.messages.create.call_args[1]
    assert "PII" in call_kwargs.get("system", "")

    # Clean message — no system hint injected
    armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": "What is the weather today?"}]
    )
    call_kwargs = client.messages.create.call_args[1]
    assert "system" not in call_kwargs or call_kwargs.get("system") is None


def test_system_hint_appended_to_existing_system_prompt():
    """Existing system prompt is preserved; hint is appended, not replaced."""
    client = make_mock_client("ok")
    armos_client = ArmosAnthropic(client)

    armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="You are a medical assistant.",
        messages=[{"role": "user", "content": "Patient John Smith, Aadhaar 2345 6789 0123"}]
    )
    call_kwargs = client.messages.create.call_args[1]
    assert "You are a medical assistant." in call_kwargs["system"]
    assert "PII" in call_kwargs["system"]


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------

def test_anthropic_streaming_masks_request_before_sending():
    """Outbound masking works the same with stream=True."""
    client = MagicMock()
    client.messages.create.return_value = make_mock_stream(["ok"])
    armos_client = ArmosAnthropic(client)

    stream = armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        stream=True,
        messages=[{"role": "user", "content": "Patient John Smith, Aadhaar 2345 6789 0123"}],
    )
    list(stream)

    call_kwargs = client.messages.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "John Smith" not in sent_content
    assert "[PII:" in sent_content


def test_anthropic_streaming_demaskes_token_in_response():
    """A PII token in the stream is demasked in the yielded event."""
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text

    client = MagicMock()
    client.messages.create.return_value = make_mock_stream([f"Hello {token}!"])
    armos_client = ArmosAnthropic(client)

    stream = armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        stream=True,
        messages=[{"role": "user", "content": "Hello John Smith"}],
    )
    text = "".join(
        e.delta.text
        for e in stream
        if e.type == "content_block_delta" and e.delta.type == "text_delta"
    )
    assert "John Smith" in text
    assert "[PII:" not in text


def test_anthropic_streaming_token_split_across_chunks():
    """Token split across chunks is reassembled and demasked."""
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text

    mid = len(token) // 2
    client = MagicMock()
    client.messages.create.return_value = make_mock_stream([token[:mid], token[mid:]])
    armos_client = ArmosAnthropic(client)

    stream = armos_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        stream=True,
        messages=[{"role": "user", "content": "Hello John Smith"}],
    )
    text = "".join(
        e.delta.text
        for e in stream
        if e.type == "content_block_delta" and e.delta.type == "text_delta"
    )
    assert "John Smith" in text
    assert "[PII:" not in text


def test_messages_demask_response_no_content():
    """_demask_response returns response unchanged when it has no content attr."""
    from armos.wrappers.anthropic import ArmosMessages
    from armos import Armos
    guard = Armos()
    mock_messages = MagicMock()
    msgs = ArmosMessages(mock_messages, guard)

    response_no_content = MagicMock(spec=[])
    result = msgs._demask_response(response_no_content)
    assert result is response_no_content


def test_messages_getattr_delegates():
    """ArmosMessages.__getattr__ forwards to underlying messages."""
    from armos.wrappers.anthropic import ArmosMessages
    from armos import Armos
    guard = Armos()
    mock_messages = MagicMock()
    mock_messages.some_method.return_value = "ok"
    msgs = ArmosMessages(mock_messages, guard)
    assert msgs.some_method() == "ok"
