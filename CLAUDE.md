# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install for development
pip install -e ".[dev,all]"

# Download spaCy model (first-time only, ~560 MB)
python -m spacy download en_core_web_lg

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_detection.py -v

# Run a single test
pytest tests/test_detection.py::test_detects_aadhaar_spaces -v

# Build for PyPI
python -m build
```

## Architecture

The request flow is: **wrapper → guard → detection engine → tokenizer → vault**

```
ArmosOpenAI / ArmosAnthropic   (wrappers/openai.py, wrappers/anthropic.py)
        │  intercept create() calls, inject SYSTEM_HINT when PII found
        ▼
    _MaskingMixin               (wrappers/base.py)
        │  shared mask/demask logic across all wrappers
        ▼
      Armos                     (guard.py)
        │  orchestrates detection + tokenization
        ├──▶ DetectionEngine    (detection/engine.py)
        │        Presidio AnalyzerEngine with spaCy en_core_web_lg
        │        Custom recognisers: Aadhaar, PAN, API keys
        │        Returns List[DetectedEntity] sorted by position
        └──▶ Tokenizer          (masking/tokenizer.py)
                 Replaces spans right-to-left (preserves offsets)
                 Token format: [PII:ENTITYTYPE:8hexhash]
                 Reads/writes BaseVault
```

**Vault** (`masking/vault/`): `BaseVault` defines the interface. `MemoryVault` is the default — ephemeral, per-process. `RedisVault` is optional, requires `pip install armos[redis]`. Token generation is deterministic — same value + entity type always produces the same token via MD5 of `"ENTITYTYPE:normalised_value"`. Casing variants map to the same token; first-seen value is restored on demask.

**Detection** (`detection/`): `DetectionEngine` builds a Presidio `AnalyzerEngine` with `en_core_web_lg`. Entity types are declared in `ENTITY_TYPES` (Presidio names) and mapped to short codes via `ENTITY_SHORT_CODES` (e.g. `PERSON → NAME`). Custom recognisers subclass Presidio's `PatternRecognizer`. Overlapping detections are resolved by keeping the higher-confidence span.

**Wrappers** (`wrappers/`): Each wrapper class proxies only the methods it intercepts (`create()`); everything else falls through via `__getattr__`. The `SYSTEM_HINT` constant in `base.py` is injected as a system message when PII is detected, instructing the LLM to reproduce tokens verbatim.

## Adding a new entity type

1. Presidio built-in: add to `ENTITY_TYPES` and `ENTITY_SHORT_CODES` in `detection/engine.py`.
2. Custom pattern: add a file under `detection/recognisers/`, subclass `PatternRecognizer`, register in `DetectionEngine._build_analyzer()`.
3. Add a test in `tests/test_detection.py` and an entry in `benchmarks/accuracy_benchmark.py`.
4. Update the detection table in `README.md`.

## Key constraints

- **Token format is stable** — `[PII:TYPE:8hexhash]`. Do not change without a migration plan; existing vaults will break.
- **No network calls during detection** — everything runs in-process. The privacy guarantee depends on this.
- **`stream=True` and async clients are not supported** — they pass through unmasked. Do not silently mask partial chunks.
- **Do not commit git changes** — the user commits and pushes all changes themselves.
