# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field
from typing import List


@dataclass
class DetectedEntity:
    """A single PII entity found in text."""
    entity_type: str
    text: str
    start: int
    end: int
    score: float


@dataclass
class MaskResult:
    """Result of a masking operation."""
    text: str
    entities: List[DetectedEntity] = field(default_factory=list)

    @property
    def has_pii(self) -> bool:
        return len(self.entities) > 0
