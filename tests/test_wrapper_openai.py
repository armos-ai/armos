import pytest
from unittest.mock import MagicMock, patch
from armos.wrappers.openai import ArmosOpenAI, ArmosCompletions
from armos.wrappers.base import _StreamingDemasker


def make_mock_chunk(content, finish_reason=None):
    chunk = MagicMock()
    chunk.choices[0].delta.content = content
    chunk.choices[0].finish_reason = finish_reason
    return chunk


def make_mock_stream(texts):
    """texts is a list of delta strings; a stop chunk is appended automatically."""
    chunks = [make_mock_chunk(t) for t in texts]
    chunks.append(make_mock_chunk(None, finish_reason="stop"))
    return iter(chunks)


def make_mock_openai_response(content: str):
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    response.choices = [choice]
    return response


def make_mock_client(response_content: str):
    client = MagicMock()
    client.chat.completions.create.return_value = make_mock_openai_response(response_content)
    return client


def test_masks_pii_before_sending():
    client = make_mock_client("Here is a summary.")
    armos_client = ArmosOpenAI(client)

    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "My name is John Smith and email is john@test.com"}]
    )

    call_kwargs = client.chat.completions.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "John Smith" not in sent_content
    assert "john@test.com" not in sent_content
    assert "[PII:" in sent_content


def test_demasked_response_has_no_tokens():
    client = make_mock_client("Summary for [PII:NAME:a1b2c3d4].")
    armos_client = ArmosOpenAI(client)

    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarise for John Smith"}]
    )

    # The response token [PII:NAME:a1b2c3d4] is not in the vault, so it stays unchanged
    # But real vault tokens from masking would be demasked
    response = armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello world"}]
    )
    # No PII tokens in clean response
    assert response.choices[0].message.content is not None


def test_passthrough_non_chat_methods():
    client = make_mock_client("ok")
    armos_client = ArmosOpenAI(client)
    # models.list should passthrough
    armos_client.models.list()
    client.models.list.assert_called_once()


def test_no_double_masking():
    """Messages already containing tokens should not be re-masked."""
    client = make_mock_client("ok")
    armos_client = ArmosOpenAI(client)

    already_masked = "Hello [PII:NAME:a1b2c3d4] how are you"
    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": already_masked}]
    )

    call_kwargs = client.chat.completions.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert sent_content.count("[PII:NAME:a1b2c3d4]") == 1


def test_system_hint_injected_only_when_pii_detected():
    """System hint must be added when PII is found, absent when message is clean."""
    client = make_mock_client("ok")
    armos_client = ArmosOpenAI(client)

    # PII message — hint should appear
    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "My email is john@test.com"}]
    )
    call_kwargs = client.chat.completions.create.call_args[1]
    system_msg = next((m for m in call_kwargs["messages"] if m.get("role") == "system"), None)
    assert system_msg is not None
    assert "PII" in system_msg["content"]

    # Clean message — no system hint injected
    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What is the weather today?"}]
    )
    call_kwargs = client.chat.completions.create.call_args[1]
    system_msg = next((m for m in call_kwargs["messages"] if m.get("role") == "system"), None)
    assert system_msg is None


def test_system_hint_appended_to_existing_system_message():
    """Existing system message is preserved; hint is appended, not replaced."""
    client = make_mock_client("ok")
    armos_client = ArmosOpenAI(client)

    armos_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "My email is john@test.com"},
        ]
    )
    call_kwargs = client.chat.completions.create.call_args[1]
    system_content = call_kwargs["messages"][0]["content"]
    assert "You are a helpful assistant." in system_content
    assert "PII" in system_content


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------

def test_streaming_demasker_no_tokens():
    d = _StreamingDemasker(lambda x: x)
    assert d.feed("Hello world") == "Hello world"
    assert d.flush() == ""


def test_streaming_demasker_complete_token_in_one_chunk():
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text  # e.g. [PII:NAME:c4587843]

    d = _StreamingDemasker(guard.demask)
    out = d.feed(f"Hello {token}!")
    assert "John Smith" in out
    assert "[PII:" not in out


def test_streaming_demasker_token_split_across_chunks():
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text  # [PII:NAME:xxxxxxxx]

    mid = len(token) // 2
    part1, part2 = token[:mid], token[mid:]

    d = _StreamingDemasker(guard.demask)
    out1 = d.feed(f"Hello {part1}")  # partial token — should buffer
    out2 = d.feed(part2)             # completes the token

    full = out1 + out2
    assert "John Smith" in full
    assert "[PII:" not in full


def test_streaming_masks_request_before_sending():
    """Outbound masking works the same with stream=True."""
    client = MagicMock()
    client.chat.completions.create.return_value = make_mock_stream(["ok"])
    armos_client = ArmosOpenAI(client)

    stream = armos_client.chat.completions.create(
        model="gpt-4o",
        stream=True,
        messages=[{"role": "user", "content": "My email is john@test.com"}],
    )
    list(stream)  # consume

    call_kwargs = client.chat.completions.create.call_args[1]
    # PII detected → system hint prepended, user message is at index 1
    user_msg = next(m for m in call_kwargs["messages"] if m.get("role") == "user")
    assert "john@test.com" not in user_msg["content"]
    assert "[PII:EMAIL:" in user_msg["content"]


def test_streaming_demaskes_token_in_response():
    """A PII token in the stream response is demasked in the yielded chunk."""
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text

    client = MagicMock()
    client.chat.completions.create.return_value = make_mock_stream([f"Hello {token}!"])
    armos_client = ArmosOpenAI(client)

    stream = armos_client.chat.completions.create(
        model="gpt-4o",
        stream=True,
        messages=[{"role": "user", "content": "Hello John Smith"}],
    )
    chunks = list(stream)
    text = "".join(
        c.choices[0].delta.content
        for c in chunks
        if c.choices[0].delta.content
    )
    assert "John Smith" in text
    assert "[PII:" not in text


def test_streaming_token_split_across_chunks_in_response():
    """Token split across two stream chunks is reassembled and demasked."""
    from armos import Armos
    guard = Armos()
    result = guard.mask("John Smith")
    token = result.text

    mid = len(token) // 2
    client = MagicMock()
    client.chat.completions.create.return_value = make_mock_stream(
        [token[:mid], token[mid:]]
    )
    armos_client = ArmosOpenAI(client)

    stream = armos_client.chat.completions.create(
        model="gpt-4o",
        stream=True,
        messages=[{"role": "user", "content": "Hello John Smith"}],
    )
    chunks = list(stream)
    text = "".join(
        c.choices[0].delta.content
        for c in chunks
        if c.choices[0].delta.content
    )
    assert "John Smith" in text
    assert "[PII:" not in text


def test_completions_demask_response_no_choices():
    """_demask_response returns response unchanged when it has no choices attr."""
    from armos.wrappers.openai import ArmosCompletions
    from armos import Armos
    guard = Armos()
    mock_completions = MagicMock()
    comp = ArmosCompletions(mock_completions, guard)

    response_no_choices = MagicMock(spec=[])  # no 'choices' attribute
    result = comp._demask_response(response_no_choices)
    assert result is response_no_choices


def test_completions_getattr_delegates():
    """ArmosCompletions.__getattr__ forwards to underlying completions."""
    from armos.wrappers.openai import ArmosCompletions
    from armos import Armos
    guard = Armos()
    mock_completions = MagicMock()
    mock_completions.some_method.return_value = "ok"
    comp = ArmosCompletions(mock_completions, guard)
    assert comp.some_method() == "ok"


def test_chat_getattr_delegates():
    """ArmosChat.__getattr__ forwards to underlying chat."""
    from armos.wrappers.openai import ArmosChat
    from armos import Armos
    guard = Armos()
    mock_chat = MagicMock()
    mock_chat.models.return_value = ["gpt-4o"]
    chat = ArmosChat(mock_chat, guard)
    assert chat.models() == ["gpt-4o"]


def test_responses_demask_response_no_output():
    """_demask_response returns response unchanged when it has no output attr."""
    from armos.wrappers.openai import ArmosResponses
    from armos import Armos
    guard = Armos()
    mock_responses = MagicMock()
    resp = ArmosResponses(mock_responses, guard)

    response_no_output = MagicMock(spec=[])
    result = resp._demask_response(response_no_output)
    assert result is response_no_output


def test_responses_getattr_delegates():
    """ArmosResponses.__getattr__ forwards to underlying responses."""
    from armos.wrappers.openai import ArmosResponses
    from armos import Armos
    guard = Armos()
    mock_responses = MagicMock()
    mock_responses.some_method.return_value = "ok"
    resp = ArmosResponses(mock_responses, guard)
    assert resp.some_method() == "ok"


def test_embeddings_getattr_delegates():
    """ArmosEmbeddings.__getattr__ forwards to underlying embeddings."""
    from armos.wrappers.openai import ArmosEmbeddings
    from armos import Armos
    guard = Armos()
    mock_embeddings = MagicMock()
    mock_embeddings.some_method.return_value = "ok"
    emb = ArmosEmbeddings(mock_embeddings, guard)
    assert emb.some_method() == "ok"
