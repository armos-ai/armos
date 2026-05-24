"""Unit tests for _MaskingMixin in wrappers/base.py."""
import pytest
from armos import Armos
from armos.wrappers.base import _MaskingMixin


class _TestWrapper(_MaskingMixin):
    """Minimal concrete class to exercise the mixin."""
    def __init__(self):
        self._guard = Armos()


@pytest.fixture
def wrapper():
    return _TestWrapper()


# ---------------------------------------------------------------------------
# _mask_string
# ---------------------------------------------------------------------------

def test_mask_string_detects_pii(wrapper):
    text, has_pii = wrapper._mask_string("Email john@test.com please")
    assert has_pii
    assert "john@test.com" not in text
    assert "[PII:EMAIL:" in text

def test_mask_string_clean_unchanged(wrapper):
    text, has_pii = wrapper._mask_string("The weather is nice today.")
    assert not has_pii
    assert text == "The weather is nice today."

def test_mask_string_skips_already_tokenised(wrapper):
    already = "Hello [PII:NAME:a1b2c3d4] how are you"
    text, has_pii = wrapper._mask_string(already)
    assert not has_pii
    assert text == already


# ---------------------------------------------------------------------------
# _mask_messages
# ---------------------------------------------------------------------------

def test_mask_messages_string_content(wrapper):
    messages = [{"role": "user", "content": "My email is john@test.com"}]
    masked, has_pii = wrapper._mask_messages(messages)
    assert has_pii
    assert "john@test.com" not in masked[0]["content"]
    assert "[PII:EMAIL:" in masked[0]["content"]

def test_mask_messages_clean_unchanged(wrapper):
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    masked, has_pii = wrapper._mask_messages(messages)
    assert not has_pii
    assert masked[0]["content"] == "Hello, how are you?"

def test_mask_messages_content_block_list(wrapper):
    messages = [{"role": "user", "content": [
        {"type": "text", "text": "Email john@test.com"},
        {"type": "image_url", "url": "http://example.com/img.png"},
    ]}]
    masked, has_pii = wrapper._mask_messages(messages)
    assert has_pii
    assert "john@test.com" not in masked[0]["content"][0]["text"]
    assert masked[0]["content"][1]["url"] == "http://example.com/img.png"

def test_mask_messages_preserves_role(wrapper):
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "My PAN is ABCDE1234F"},
    ]
    masked, has_pii = wrapper._mask_messages(messages)
    assert has_pii
    assert masked[0]["role"] == "system"
    assert masked[0]["content"] == "You are helpful."
    assert masked[1]["role"] == "user"

def test_mask_messages_no_double_masking(wrapper):
    messages = [{"role": "user", "content": "Hello [PII:NAME:a1b2c3d4]"}]
    masked, has_pii = wrapper._mask_messages(messages)
    assert not has_pii
    assert masked[0]["content"].count("[PII:NAME:a1b2c3d4]") == 1


# ---------------------------------------------------------------------------
# _mask_input_list
# ---------------------------------------------------------------------------

def test_mask_input_list_masks_pii_items(wrapper):
    items = ["john@test.com", "no pii here"]
    masked, has_pii = wrapper._mask_input_list(items)
    assert has_pii
    assert "john@test.com" not in masked[0]
    assert "[PII:EMAIL:" in masked[0]
    assert masked[1] == "no pii here"

def test_mask_input_list_all_clean(wrapper):
    items = ["hello world", "no pii here"]
    masked, has_pii = wrapper._mask_input_list(items)
    assert not has_pii
    assert masked == items

def test_mask_input_list_non_string_passthrough(wrapper):
    items = [[1, 2, 3], "john@test.com"]
    masked, has_pii = wrapper._mask_input_list(items)
    assert masked[0] == [1, 2, 3]
    assert has_pii
