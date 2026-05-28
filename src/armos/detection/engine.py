# SPDX-License-Identifier: MIT
from typing import List
import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from ..models import DetectedEntity
from .recognisers.aadhaar import AadhaarRecogniser
from .recognisers.pan import PANRecogniser
from .recognisers.standard import APIKeyRecogniser
from .recognisers.address import PhysicalAddressRecogniser

_MODEL = "en_core_web_lg"


def _ensure_model() -> None:
    if not spacy.util.is_package(_MODEL):
        print(f"[armos] Downloading spaCy model {_MODEL!r} (first-time setup, ~560 MB)...")
        spacy.cli.download(_MODEL)
        print("[armos] Model ready.")


ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "AADHAAR_NUMBER",
    "IN_PAN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "API_KEY",
    "US_SSN",
    "IBAN_CODE",
    "PHYSICAL_ADDRESS",
]

ENTITY_SHORT_CODES = {
    "PERSON":           "NAME",
    "EMAIL_ADDRESS":    "EMAIL",
    "PHONE_NUMBER":     "PHONE",
    "AADHAAR_NUMBER":   "AADHAAR",
    "IN_PAN":           "PAN",
    "CREDIT_CARD":      "CARD",
    "IP_ADDRESS":       "IP",
    "API_KEY":          "APIKEY",
    "US_SSN":           "SSN",
    "IBAN_CODE":        "IBAN",
    "PHYSICAL_ADDRESS": "ADDRESS",
}


class DetectionEngine:
    """
    Orchestrates all PII recognisers.
    Detection runs entirely locally — no text is sent anywhere.
    """

    def __init__(self):
        _ensure_model()
        self._analyzer = self._build_analyzer()

    def _build_analyzer(self) -> AnalyzerEngine:
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": _MODEL}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)

        registry.add_recognizer(AadhaarRecogniser())
        registry.add_recognizer(PANRecogniser())
        registry.add_recognizer(APIKeyRecogniser())
        registry.add_recognizer(PhysicalAddressRecogniser())

        return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)

    def detect(self, text: str, language: str = "en") -> List[DetectedEntity]:
        """Detect all PII in text. Returns entities sorted by position."""
        if not text or not text.strip():
            return []

        results = self._analyzer.analyze(
            text=text,
            entities=ENTITY_TYPES,
            language=language,
        )

        entities = [
            DetectedEntity(
                entity_type=ENTITY_SHORT_CODES.get(r.entity_type, r.entity_type),
                text=text[r.start:r.end],
                start=r.start,
                end=r.end,
                score=r.score,
            )
            for r in results
        ]

        entities.sort(key=lambda e: e.start)
        return self._resolve_overlaps(entities)

    def detect_all(self, text: str, language: str = "en") -> tuple:
        """
        Detect PII at a lower threshold to surface near-misses.
        Returns (certain, uncertain) where:
          certain   — score >= 0.35, will be masked
          uncertain — score 0.1–0.35, detected but not masked
        """
        if not text or not text.strip():
            return [], []

        results = self._analyzer.analyze(
            text=text,
            entities=ENTITY_TYPES,
            language=language,
            score_threshold=0.1,
        )

        certain, uncertain = [], []
        for r in results:
            entity = DetectedEntity(
                entity_type=ENTITY_SHORT_CODES.get(r.entity_type, r.entity_type),
                text=text[r.start:r.end],
                start=r.start,
                end=r.end,
                score=r.score,
            )
            if r.score >= 0.35:
                certain.append(entity)
            else:
                uncertain.append(entity)

        certain.sort(key=lambda e: e.start)
        uncertain.sort(key=lambda e: e.start)
        return self._resolve_overlaps(certain), uncertain

    def _resolve_overlaps(self, entities: List[DetectedEntity]) -> List[DetectedEntity]:
        """Remove overlapping detections. Higher confidence wins."""
        if not entities:
            return entities

        resolved = [entities[0]]
        for current in entities[1:]:
            previous = resolved[-1]
            if current.start < previous.end:
                if current.score > previous.score:
                    resolved[-1] = current
            else:
                resolved.append(current)
        return resolved
