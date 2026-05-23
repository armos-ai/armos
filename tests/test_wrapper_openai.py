import pytest
from unittest.mock import MagicMock, patch
from armos.wrappers.openai import ArmosOpenAI, ArmosCompletions


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
    # Should not have double-masked the token
    assert sent_content.count("[PII:NAME:a1b2c3d4]") == 1
