# SPDX-License-Identifier: MIT
import re
from typing import List
from ..models import DetectedEntity, MaskResult
from .vault.base import BaseVault


TOKEN_PATTERN = re.compile(r'\[PII:[A-Z]+:[a-f0-9]{8}\]')


class Tokenizer:
    """Handles text transformation: mask() and demask()."""

    def __init__(self, vault: BaseVault):
        self._vault = vault

    def mask(self, text: str, entities: List[DetectedEntity]) -> MaskResult:
        """
        Replace detected entities with tokens.
        Processes right-to-left to preserve character positions.
        """
        if not entities:
            return MaskResult(text=text, entities=[], uncertain=[])

        masked_text = text
        for entity in reversed(entities):
            token = self._vault.store(entity.text, entity.entity_type)
            masked_text = (
                masked_text[:entity.start]
                + token
                + masked_text[entity.end:]
            )

        return MaskResult(text=masked_text, entities=list(entities))

    def demask(self, text: str) -> str:
        """
        Replace all tokens with their real values.
        Tokens not found in vault are left unchanged.
        """
        if not text:
            return text

        def replace_token(match: re.Match) -> str:
            token = match.group(0)
            real_value = self._vault.retrieve(token)
            return real_value if real_value is not None else token

        return TOKEN_PATTERN.sub(replace_token, text)

    @staticmethod
    def contains_tokens(text: str) -> bool:
        """Check if text already contains Armos tokens — avoids double-masking."""
        return bool(TOKEN_PATTERN.search(text))
