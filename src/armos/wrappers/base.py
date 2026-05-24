# SPDX-License-Identifier: MIT
from typing import Any, List

SYSTEM_HINT = "Reproduce any [PII:TYPE:HASH] tokens in your response exactly as written."


class _MaskingMixin:
    """
    Common masking utilities shared across all SDK wrappers.

    Subclasses must set self._guard (an Armos instance) before calling any method.
    """

    def _mask_string(self, text: str) -> tuple:
        """Mask a single string. Returns (masked_text, has_pii)."""
        if self._guard._tokenizer.contains_tokens(text):
            return text, False
        result = self._guard.mask(text)
        return (result.text, True) if result.has_pii else (text, False)

    def _mask_messages(self, messages: List[dict]) -> tuple:
        """
        Mask PII in a list of message dicts.
        Handles both string content and content block lists.
        Returns (masked_messages, has_pii).
        """
        masked = []
        any_pii = False
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                masked_text, pii = self._mask_string(content)
                if pii:
                    any_pii = True
                    msg = {**msg, "content": masked_text}
            elif isinstance(content, list):
                masked_blocks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        masked_text, pii = self._mask_string(text)
                        if pii:
                            any_pii = True
                            block = {**block, "text": masked_text}
                    masked_blocks.append(block)
                msg = {**msg, "content": masked_blocks}
            masked.append(msg)
        return masked, any_pii

    def _mask_input_list(self, items: list) -> tuple:
        """
        Mask a list of strings (e.g. embeddings input).
        Returns (masked_items, has_pii).
        """
        masked = []
        any_pii = False
        for item in items:
            if isinstance(item, str):
                masked_text, pii = self._mask_string(item)
                if pii:
                    any_pii = True
                masked.append(masked_text)
            else:
                masked.append(item)
        return masked, any_pii
