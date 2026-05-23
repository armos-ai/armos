import pytest
from armos.masking.tokenizer import Tokenizer
from armos.masking.vault.memory import MemoryVault
from armos.models import DetectedEntity


@pytest.fixture
def tokenizer():
    return Tokenizer(MemoryVault())


def test_mask_replaces_entity(tokenizer):
    entities = [DetectedEntity(entity_type="EMAIL", text="john@test.com", start=9, end=22, score=0.99)]
    result = tokenizer.mask("Contact john@test.com please", entities)
    assert "john@test.com" not in result.text
    assert "[PII:EMAIL:" in result.text

def test_mask_preserves_surrounding_text(tokenizer):
    entities = [DetectedEntity(entity_type="NAME", text="Alice", start=6, end=11, score=0.85)]
    result = tokenizer.mask("Hello Alice!", entities)
    assert result.text.startswith("Hello ")
    assert result.text.endswith("!")

def test_mask_multiple_entities(tokenizer):
    entities = [
        DetectedEntity(entity_type="NAME", text="Bob", start=0, end=3, score=0.9),
        DetectedEntity(entity_type="EMAIL", text="bob@x.com", start=7, end=16, score=0.99),
    ]
    result = tokenizer.mask("Bob at bob@x.com", entities)
    assert "Bob" not in result.text
    assert "bob@x.com" not in result.text

def test_demask_restores(tokenizer):
    vault = tokenizer._vault
    token = vault.store("Jane", "NAME")
    assert tokenizer.demask(f"Hello {token}!") == "Hello Jane!"

def test_demask_unknown_token_unchanged(tokenizer):
    text = "Hi [PII:NAME:deadbeef] there"
    assert tokenizer.demask(text) == text

def test_contains_tokens_true(tokenizer):
    assert Tokenizer.contains_tokens("Hello [PII:NAME:a1b2c3d4] world")

def test_contains_tokens_false(tokenizer):
    assert not Tokenizer.contains_tokens("Hello world")

def test_empty_entities(tokenizer):
    result = tokenizer.mask("no pii here", [])
    assert result.text == "no pii here"
    assert result.entities == []
