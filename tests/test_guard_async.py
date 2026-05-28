import asyncio
import pytest
from armos import Armos, MaskResult


@pytest.fixture
def guard():
    return Armos()


async def test_amask_returns_mask_result(guard):
    result = await guard.amask("Hello John Smith")
    assert isinstance(result, MaskResult)


async def test_amask_replaces_email(guard):
    result = await guard.amask("Email john@test.com for details")
    assert "john@test.com" not in result.text
    assert "[PII:EMAIL:" in result.text


async def test_amask_empty_string(guard):
    result = await guard.amask("")
    assert result.text == ""
    assert result.entities == []


async def test_amask_no_pii(guard):
    result = await guard.amask("The weather today is sunny.")
    assert result.has_pii is False
    assert result.text == "The weather today is sunny."


async def test_ademask_restores_token(guard):
    mask_result = await guard.amask("Contact john@example.com")
    restored = await guard.ademask(mask_result.text)
    assert restored == "Contact john@example.com"


async def test_amask_ademask_roundtrip(guard):
    original = "Call John Smith at john@example.com about Aadhaar 2345 6789 0123"
    masked = await guard.amask(original)
    restored = await guard.ademask(masked.text)
    assert restored == original


async def test_amask_concurrent(guard):
    """Concurrent mask calls share the same vault — all must succeed."""
    texts = [
        "Email john@test.com",
        "Call +91 98765 43210",
        "Card 4111 1111 1111 1111",
        "Key sk-abc123def456ghi789jkl012mno345pqr",
    ]
    results = await asyncio.gather(*[guard.amask(t) for t in texts])
    assert all(isinstance(r, MaskResult) for r in results)
    assert all(r.has_pii for r in results)


async def test_amask_address(guard):
    result = await guard.amask("Ship to 123 Main Street, please process.")
    assert result.has_pii is True
    assert "[PII:ADDRESS:" in result.text
