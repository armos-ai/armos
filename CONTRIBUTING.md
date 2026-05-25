# Contributing to Armos

Thanks for your interest in contributing. This document covers everything you need to get started.

---

## Setup

```bash
git clone https://github.com/armos-ai/armos-python
cd armos-python
pip install -e ".[dev,all]"
```

The spaCy model downloads automatically on first use. To pre-download it explicitly:
```bash
python -m spacy download en_core_web_lg
```

Requires Python 3.10+.

---

## Running tests

```bash
pytest tests/ -v
```

All tests must pass before submitting a PR. CI runs the full suite across Python 3.10, 3.11, and 3.12 automatically on every push.

---

## Project structure

```
src/armos/
├── core.py                  # Armos main class (mask / demask)
├── models.py                # DetectedEntity, MaskResult
├── detection/
│   ├── engine.py            # DetectionEngine — Presidio + spaCy orchestration
│   └── recognisers/
│       ├── aadhaar.py       # Custom Aadhaar regex recogniser
│       ├── pan.py           # Custom PAN regex recogniser
│       └── standard.py      # API key recogniser
├── masking/
│   ├── tokenizer.py         # Token generation and format
│   └── vault/
│       ├── memory.py        # In-memory vault
│       └── redis.py         # Redis-backed vault
└── wrappers/
    ├── base.py              # _MaskingMixin shared logic
    ├── openai.py            # ArmosOpenAI, ArmosChat, ArmosResponses, ArmosEmbeddings
    └── anthropic.py         # ArmosAnthropic, ArmosMessages
```

---

## Adding a new entity type

1. If it's a Presidio built-in (check `presidio-analyzer` docs), add it to `ENTITY_TYPES` and `ENTITY_SHORT_CODES` in `detection/engine.py`.
2. If it needs a custom recogniser, add a new file under `detection/recognisers/`, subclass `PatternRecognizer`, and register it in `DetectionEngine._build_analyzer`.
3. Add a detection test in `tests/test_detection.py`.
4. Add the entity to the accuracy benchmark in `benchmarks/accuracy_benchmark.py`.
5. Update the detection table in `README.md`.

---

## What makes a good PR

- **One thing per PR** — a new entity type, a bug fix, a wrapper improvement. Mixed PRs are hard to review.
- **Tests included** — every behaviour change needs a test. Detection changes need both a unit test and a benchmark entry.
- **No breaking changes without discussion** — token format, vault API, and wrapper signatures are stable. Open an issue first if you need to change them.
- **Keep it simple** — Armos is intentionally a thin layer. Avoid abstractions that don't have an immediate use case.

---

## Reporting issues

Open an issue at [github.com/armos-ai/armos-python/issues](https://github.com/armos-ai/armos-python/issues).

For detection misses or false positives, include:
- The input text (redact real PII — use a fake example that reproduces the issue)
- The entity type you expected to be detected
- The `armos` version (`pip show armos`)

---

## License

By contributing, you agree your changes will be licensed under the [MIT License](LICENSE).
