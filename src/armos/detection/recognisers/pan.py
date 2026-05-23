# SPDX-License-Identifier: MIT
from presidio_analyzer import Pattern, PatternRecognizer


class PANRecogniser(PatternRecognizer):
    """
    Detects Indian PAN (Permanent Account Number).

    Format: AAAAA9999A
        5 uppercase letters + 4 digits + 1 uppercase letter
    """

    PATTERNS = [
        Pattern(
            name="pan_uppercase",
            regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
            score=0.95,
        ),
        Pattern(
            name="pan_lowercase",
            regex=r"\b[a-z]{5}[0-9]{4}[a-z]{1}\b",
            score=0.85,
        ),
    ]

    CONTEXT = [
        "pan", "pan card", "pan number", "permanent account",
        "income tax", "tax id", "taxpayer", "it pan"
    ]

    def __init__(self):
        super().__init__(
            supported_entity="IN_PAN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )
