# SPDX-License-Identifier: MIT
from presidio_analyzer import Pattern, PatternRecognizer


class AadhaarRecogniser(PatternRecognizer):
    """
    Detects Indian Aadhaar numbers.

    Format: 12 digits. First digit cannot be 0 or 1.
    Common representations:
        2345 6789 0123   (spaces — most common)
        2345-6789-0123   (hyphens)
        234567890123     (no separator — lower confidence)
    """

    PATTERNS = [
        Pattern(
            name="aadhaar_spaces",
            regex=r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b",
            score=0.95,
        ),
        Pattern(
            name="aadhaar_hyphens",
            regex=r"\b[2-9]\d{3}-\d{4}-\d{4}\b",
            score=0.95,
        ),
        Pattern(
            name="aadhaar_plain",
            regex=r"\b[2-9]\d{11}\b",
            score=0.6,
        ),
    ]

    CONTEXT = [
        "aadhaar", "aadhar", "uid", "uidai",
        "unique identification", "biometric id", "aadhaaar"
    ]

    def __init__(self):
        super().__init__(
            supported_entity="AADHAAR_NUMBER",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )
