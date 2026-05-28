import pytest
from unittest.mock import AsyncMock, MagicMock
from armos import ArmosAsyncAnthropic


def _make_response(text: str):
    response = MagicMock()
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.messages = MagicMock()
    return client


@pytest.fixture
def armos(mock_client):
    return ArmosAsyncAnthropic(mock_client)


async def test_messages_masks_pii(armos, mock_client):
    mock_client.messages.create = AsyncMock(return_value=_make_response("ok"))

    await armos.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "My email is priya@acme.com"}],
    )

    sent = mock_client.messages.create.call_args.kwargs["messages"]
    assert "priya@acme.com" not in sent[0]["content"]
    assert "[PII:EMAIL:" in sent[0]["content"]


async def test_messages_injects_system_hint(armos, mock_client):
    mock_client.messages.create = AsyncMock(return_value=_make_response("ok"))

    await armos.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "Aadhaar: 2345 6789 0123"}],
    )

    system = mock_client.messages.create.call_args.kwargs.get("system", "")
    assert "PII" in system


async def test_messages_preserves_existing_system(armos, mock_client):
    mock_client.messages.create = AsyncMock(return_value=_make_response("ok"))

    await armos.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Email: bob@test.com"}],
    )

    system = mock_client.messages.create.call_args.kwargs["system"]
    assert "You are a helpful assistant." in system
    assert "PII" in system


async def test_messages_demaskes_response(armos, mock_client):
    token = armos._guard._vault.store("priya@acme.com", "EMAIL")
    mock_client.messages.create = AsyncMock(
        return_value=_make_response(f"Hello {token}")
    )

    result = await armos.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "Hi"}],
    )
    assert result.content[0].text == "Hello priya@acme.com"


async def test_messages_no_hint_without_pii(armos, mock_client):
    mock_client.messages.create = AsyncMock(return_value=_make_response("ok"))

    await armos.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )

    kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" not in kwargs or kwargs.get("system") is None


async def test_getattr_passthrough(armos, mock_client):
    mock_client.models = MagicMock()
    assert armos.models is mock_client.models
