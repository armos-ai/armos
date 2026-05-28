import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from armos import ArmosAsyncOpenAI


def _make_response(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.responses = MagicMock()
    client.embeddings = MagicMock()
    return client


@pytest.fixture
def armos(mock_client):
    return ArmosAsyncOpenAI(mock_client)


async def test_completions_masks_pii_in_messages(armos, mock_client):
    mock_client.chat.completions.create = AsyncMock(return_value=_make_response("ok"))

    await armos.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Email is john@test.com"}],
    )

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in sent_messages if m["role"] == "user")
    assert "john@test.com" not in user_content
    assert "[PII:EMAIL:" in user_content


async def test_completions_injects_system_hint_when_pii(armos, mock_client):
    mock_client.chat.completions.create = AsyncMock(return_value=_make_response("ok"))

    await armos.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Email is john@test.com"}],
    )

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    system_msgs = [m for m in sent_messages if m["role"] == "system"]
    assert any("PII" in m["content"] for m in system_msgs)


async def test_completions_demaskes_response(armos, mock_client):
    # Pre-store a token so we can verify demasking
    token = armos._guard._vault.store("john@example.com", "EMAIL")
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_response(f"Reply to {token}")
    )

    result = await armos.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Reply"}],
    )
    assert result.choices[0].message.content == "Reply to john@example.com"


async def test_completions_no_masking_when_no_pii(armos, mock_client):
    mock_client.chat.completions.create = AsyncMock(return_value=_make_response("ok"))

    await armos.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What is 2 + 2?"}],
    )

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    # No system hint injected when there's no PII
    assert all(m["role"] != "system" for m in sent_messages)


async def test_embeddings_masks_string_input(armos, mock_client):
    mock_client.embeddings.create = AsyncMock(return_value=MagicMock())

    await armos.embeddings.create(
        model="text-embedding-3-small",
        input="Email: john@test.com",
    )

    sent_input = mock_client.embeddings.create.call_args.kwargs["input"]
    assert "john@test.com" not in sent_input
    assert "[PII:EMAIL:" in sent_input


async def test_embeddings_masks_list_input(armos, mock_client):
    mock_client.embeddings.create = AsyncMock(return_value=MagicMock())

    await armos.embeddings.create(
        model="text-embedding-3-small",
        input=["Call 9876543210", "No PII here"],
    )

    sent_input = mock_client.embeddings.create.call_args.kwargs["input"]
    assert "9876543210" not in sent_input[0]
    assert sent_input[1] == "No PII here"


async def test_getattr_passthrough(armos, mock_client):
    mock_client.models = MagicMock()
    assert armos.models is mock_client.models
