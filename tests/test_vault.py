import pytest
from armos.masking.vault.memory import MemoryVault


def test_store_and_retrieve():
    vault = MemoryVault()
    token = vault.store("John Smith", "NAME")
    assert vault.retrieve(token) == "John Smith"

def test_token_format():
    import re
    vault = MemoryVault()
    token = vault.store("John Smith", "NAME")
    assert re.match(r'\[PII:NAME:[a-f0-9]{8}\]', token)

def test_consistency_same_value():
    vault = MemoryVault()
    token1 = vault.store("John Smith", "NAME")
    token2 = vault.store("John Smith", "NAME")
    assert token1 == token2

def test_casing_same_token_for_all_variants():
    """
    All casing variants of the same name produce the SAME token.
    LLM sees one consistent entity across all variants.
    First-seen value is stored for de-masking.
    """
    vault = MemoryVault()
    token1 = vault.store("john smith", "NAME")
    token2 = vault.store("John Smith", "NAME")
    token3 = vault.store("JOHN SMITH", "NAME")
    assert token1 == token2 == token3
    assert vault.retrieve(token1) == "john smith"

def test_different_values_different_tokens():
    vault = MemoryVault()
    token1 = vault.store("John Smith", "NAME")
    token2 = vault.store("Jane Doe", "NAME")
    assert token1 != token2

def test_clear():
    vault = MemoryVault()
    token = vault.store("John Smith", "NAME")
    vault.clear()
    assert vault.retrieve(token) is None

def test_unknown_token_returns_none():
    vault = MemoryVault()
    assert vault.retrieve("[PII:NAME:unknown1]") is None

def test_generate_token_in_base():
    """Token generation is shared logic in BaseVault."""
    vault = MemoryVault()
    t1 = vault.generate_token("John Smith", "NAME")
    t2 = vault.generate_token("John Smith", "NAME")
    assert t1 == t2
    assert t1.startswith("[PII:NAME:")
