# SPDX-License-Identifier: MIT
from typing import Dict, Optional
from .base import BaseVault


class MemoryVault(BaseVault):
    """
    In-memory vault. Lives for the lifetime of the Armos instance.
    Zero configuration required. Default vault.
    """

    def __init__(self):
        self._forward: Dict[str, str] = {}
        self._reverse: Dict[str, str] = {}

    def store(self, real_value: str, entity_type: str) -> str:
        reverse_key = self.make_reverse_key(real_value, entity_type)

        if reverse_key in self._reverse:
            return self._reverse[reverse_key]

        token = self.generate_token(real_value, entity_type)
        self._forward[token] = real_value
        self._reverse[reverse_key] = token
        return token

    def retrieve(self, token: str) -> Optional[str]:
        return self._forward.get(token)

    def clear(self) -> None:
        self._forward.clear()
        self._reverse.clear()

    def __len__(self) -> int:
        return len(self._forward)
