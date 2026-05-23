# SPDX-License-Identifier: MIT
from .models import MaskResult
from .detection.engine import DetectionEngine
from .masking.tokenizer import Tokenizer
from .masking.vault import build_vault
from .masking.vault.base import BaseVault
from .masking.vault.redis import RedisVault


class Armos:
    """
    Core privacy engine.

    Exposes mask() and demask() as standalone methods.
    Used internally by ArmosOpenAI and ArmosAnthropic wrappers.
    Can also be used directly for custom LLM integrations.
    """

    def __init__(self, store: str | None = None, vault_ttl: int = RedisVault.DEFAULT_TTL):
        self._vault: BaseVault = build_vault(store=store, ttl=vault_ttl)
        self._engine = DetectionEngine()
        self._tokenizer = Tokenizer(self._vault)

    def mask(self, text: str) -> MaskResult:
        """Detect and mask all PII in text."""
        if not text:
            return MaskResult(text=text or "", entities=[])

        entities = self._engine.detect(text)
        return self._tokenizer.mask(text, entities)

    def demask(self, text: str) -> str:
        """Restore all tokens in text to their real values."""
        return self._tokenizer.demask(text)

    def clear_vault(self) -> None:
        """Clear all stored token mappings."""
        self._vault.clear()
