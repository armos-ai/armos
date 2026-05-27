# SPDX-License-Identifier: MIT
import hashlib
from abc import ABC, abstractmethod
from typing import Optional


class BaseVault(ABC):
    """
    Abstract vault. Stores token <-> real value mappings.

    Token generation uses NORMALISED value (lowercased, stripped).
    All casing variants of the same entity produce the same token.
    De-masking restores the first-seen occurrence (first casing wins).
    """

    TOKEN_PREFIX = "PII"

    def generate_token(self, real_value: str, entity_type: str) -> str:
        normalised = real_value.strip().lower()
        hash_suffix = hashlib.md5(
            f"{entity_type}:{normalised}".encode()
        ).hexdigest()[:8]
        return f"[{self.TOKEN_PREFIX}:{entity_type.upper()}:{hash_suffix}]"

    def make_reverse_key(self, real_value: str, entity_type: str) -> str:
        normalised = real_value.strip().lower()
        return f"{entity_type.upper()}:{normalised}"

    @abstractmethod
    def store(self, real_value: str, entity_type: str) -> str:  # pragma: no cover
        pass

    @abstractmethod
    def retrieve(self, token: str) -> Optional[str]:  # pragma: no cover
        pass

    @abstractmethod
    def clear(self) -> None:  # pragma: no cover
        pass
