# SPDX-License-Identifier: MIT
"""
Armos — Automatic PII masking for OpenAI and Anthropic SDKs.

One line change. PII never reaches your LLM provider.

Quick start:
    from openai import OpenAI
    from armos import ArmosOpenAI

    client = ArmosOpenAI(OpenAI())
    # Use exactly as you would the normal OpenAI client.
    # PII is masked automatically before every request.
    # Real values are restored automatically in every response.
"""

from .guard import Armos
from .wrappers.openai import ArmosOpenAI
from .wrappers.anthropic import ArmosAnthropic
from .models import MaskResult, DetectedEntity

__version__ = "0.1.1"
__all__ = [
    "Armos",
    "ArmosOpenAI",
    "ArmosAnthropic",
    "MaskResult",
    "DetectedEntity",
]
