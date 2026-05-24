"""Tests for Responses API and Embeddings masking (v1.0 features)."""
from unittest.mock import MagicMock
from armos.wrappers.openai import ArmosOpenAI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_responses_client(text: str):
    block = MagicMock()
    block.text = text
    item = MagicMock()
    item.content = [block]
    response = MagicMock()
    response.output = [item]
    client = MagicMock()
    client.responses.create.return_value = response
    return client


def make_embeddings_client():
    client = MagicMock()
    client.embeddings.create.return_value = MagicMock()
    return client


# ---------------------------------------------------------------------------
# Responses API
# ---------------------------------------------------------------------------

def test_responses_masks_pii_in_string_input():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    armos.responses.create(model="gpt-4o", input="Email john@test.com for help")

    call_kwargs = client.responses.create.call_args[1]
    assert "john@test.com" not in call_kwargs["input"]
    assert "[PII:" in call_kwargs["input"]


def test_responses_system_hint_injected_when_pii():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    armos.responses.create(model="gpt-4o", input="Email john@test.com for help")

    call_kwargs = client.responses.create.call_args[1]
    assert "PII" in call_kwargs.get("instructions", "")


def test_responses_no_hint_when_clean():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    armos.responses.create(model="gpt-4o", input="What is the weather today?")

    call_kwargs = client.responses.create.call_args[1]
    assert "instructions" not in call_kwargs or not call_kwargs.get("instructions")


def test_responses_existing_instructions_preserved():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    armos.responses.create(
        model="gpt-4o",
        input="Email john@test.com",
        instructions="You are a helpful assistant.",
    )

    call_kwargs = client.responses.create.call_args[1]
    assert "You are a helpful assistant." in call_kwargs["instructions"]
    assert "PII" in call_kwargs["instructions"]


def test_responses_demasked_output():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    result = armos.responses.create(model="gpt-4o", input="Contact john@test.com")
    # output text is demasked — mock returns "ok" which has no tokens, stays unchanged
    assert result.output[0].content[0].text == "ok"


def test_responses_masks_list_input():
    client = make_responses_client("ok")
    armos = ArmosOpenAI(client)

    armos.responses.create(
        model="gpt-4o",
        input=[{"role": "user", "content": "My email is john@test.com"}]
    )

    call_kwargs = client.responses.create.call_args[1]
    sent_content = call_kwargs["input"][0]["content"]
    assert "john@test.com" not in sent_content
    assert "[PII:" in sent_content


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def test_embeddings_masks_string_input():
    client = make_embeddings_client()
    armos = ArmosOpenAI(client)

    armos.embeddings.create(model="text-embedding-3-small", input="john@test.com")

    call_kwargs = client.embeddings.create.call_args[1]
    assert "john@test.com" not in call_kwargs["input"]
    assert "[PII:" in call_kwargs["input"]


def test_embeddings_masks_list_input():
    client = make_embeddings_client()
    armos = ArmosOpenAI(client)

    armos.embeddings.create(
        model="text-embedding-3-small",
        input=["john@test.com", "no pii here"]
    )

    call_kwargs = client.embeddings.create.call_args[1]
    assert "john@test.com" not in call_kwargs["input"][0]
    assert "[PII:" in call_kwargs["input"][0]
    assert call_kwargs["input"][1] == "no pii here"


def test_embeddings_clean_input_unchanged():
    client = make_embeddings_client()
    armos = ArmosOpenAI(client)

    armos.embeddings.create(
        model="text-embedding-3-small",
        input="The quarterly results were strong."
    )

    call_kwargs = client.embeddings.create.call_args[1]
    assert call_kwargs["input"] == "The quarterly results were strong."


def test_embeddings_passthrough():
    client = make_embeddings_client()
    armos = ArmosOpenAI(client)
    armos.embeddings.create(model="text-embedding-3-small", input="hello")
    client.embeddings.create.assert_called_once()
