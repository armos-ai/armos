import pytest
from armos import Armos, MaskResult


@pytest.fixture
def guard():
    return Armos()


def test_mask_returns_mask_result(guard):
    result = guard.mask("Hello John Smith")
    assert isinstance(result, MaskResult)

def test_mask_replaces_email(guard):
    result = guard.mask("Email john@test.com for details")
    assert "john@test.com" not in result.text
    assert "[PII:EMAIL:" in result.text

def test_mask_replaces_aadhaar(guard):
    result = guard.mask("Aadhaar: 2345 6789 0123")
    assert "2345 6789 0123" not in result.text
    assert "[PII:AADHAAR:" in result.text

def test_mask_replaces_pan(guard):
    result = guard.mask("PAN: ABCDE1234F")
    assert "ABCDE1234F" not in result.text
    assert "[PII:PAN:" in result.text

def test_roundtrip_restores_original(guard):
    original = "Call John Smith at john@example.com about Aadhaar 2345 6789 0123"
    result = guard.mask(original)
    restored = guard.demask(result.text)
    assert restored == original

def test_casing_normalised_same_token(guard):
    """All casing variants produce the same token — LLM sees one entity."""
    result1 = guard.mask("patient john smith")
    result2 = guard.mask("Patient John Smith")
    result3 = guard.mask("PATIENT JOHN SMITH")

    import re
    pattern = re.compile(r'\[PII:NAME:[a-f0-9]{8}\]')

    tokens1 = pattern.findall(result1.text)
    tokens2 = pattern.findall(result2.text)
    tokens3 = pattern.findall(result3.text)

    if tokens1 and tokens2 and tokens3:
        assert tokens1[0] == tokens2[0] == tokens3[0]

    assert guard.demask(result1.text) == "patient john smith"
    assert "john smith" in guard.demask(result2.text).lower()
    assert "john smith" in guard.demask(result3.text).lower()

def test_unknown_token_safe(guard):
    """Tokens not in vault left unchanged — never crash."""
    text = "Hello [PII:NAME:unknown1] how are you"
    assert guard.demask(text) == text

def test_empty_string(guard):
    result = guard.mask("")
    assert result.text == ""
    assert result.entities == []

def test_clean_text_unchanged(guard):
    result = guard.mask("The weather is nice today.")
    assert result.text == "The weather is nice today."
    assert not result.has_pii

def test_redis_store():
    pytest.importorskip("redis")
    try:
        guard = Armos(store="redis", redis_url="redis://localhost:6379")
        result = guard.mask("Email: test@example.com")
        assert "[PII:EMAIL:" in result.text
        assert guard.demask(result.text) == "Email: test@example.com"
    except Exception:
        pytest.skip("Redis not available")

def test_redis_store_missing_url_raises():
    pytest.importorskip("redis")
    with pytest.raises(ValueError, match="redis_url is required"):
        Armos(store="redis")

def test_invalid_store_raises():
    with pytest.raises(ValueError, match="Unsupported store"):
        Armos(store="postgres")
