# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] — 2026-05-28

### Added
- **Streaming demasking** — OpenAI (`chat.completions`) and Anthropic (`messages`) wrappers now transparently demasked PII tokens in streaming responses. Tokens split across multiple chunks are buffered and reassembled before demasking.
- **Uncertain PII detection** — `MaskResult.uncertain` exposes entities that scored below the masking threshold (0.35) but above a near-miss floor (0.1). These are surfaced for inspection without being masked.

### Fixed
- Added `click>=8.0.0` as an explicit dependency. `typer>=0.12` dropped `click` as a hard requirement, causing `ModuleNotFoundError` on CI when spaCy's CLI tried to import it.

---

## [1.2.1] — 2026-05-14

### Added
- Redis vault now supports TLS (`rediss://`) connections via `certifi` for CA bundle verification.
- `certifi>=2024.0.0` added to the `redis` and `all` extras.

---

## [1.2.0] — 2026-05-12

### Added
- Auto-download of `en_core_web_lg` spaCy model on first use — no manual `spacy download` required.
- `CONTRIBUTING.md` with setup, testing, and PR guidelines.

---

## [1.1.0] — 2026-05-10

### Changed
- Dropped Python 3.9 support; minimum version is now **Python 3.10**.
- Added GitHub Actions CI running tests across Python 3.10, 3.11, and 3.12.

---

## [1.0.1] — 2026-05-08

### Added
- Detection accuracy benchmarks across all supported entity types (NAME, EMAIL, PHONE, AADHAAR, PAN, CARD, IP, APIKEY, SSN, IBAN).

---

## [1.0.0] — 2026-05-07

### Added
- **SSN detection** — US Social Security Numbers (e.g. `371-53-1234`).
- **IBAN detection** — International Bank Account Numbers (e.g. `GB29NWBK60161331926819`).
- **OpenAI Responses API masking** — `client.responses.create(...)` is now protected.
- **Embeddings masking** — `client.embeddings.create(...)` masks PII before the vector is generated.
- `QUICKSTART.md` and `TROUBLESHOOTING.md` guides.

---

## [0.1.7] — 2026-04-28

### Changed
- Redis store API refactored to explicit `store="redis"` + `redis_url=` parameters (breaking change from earlier implicit config).
- System hint automatically injected into the LLM context when PII is detected, reminding the model to preserve tokens verbatim.

---

## [0.1.1] — 2026-04-20

### Changed
- Enriched PyPI package metadata (classifiers, keywords, URLs).

---

## [0.1.0] — 2026-04-18

### Added
- Initial release.
- Core PII masking via Presidio + spaCy `en_core_web_lg`.
- Supported entities: NAME, EMAIL, PHONE, AADHAAR, PAN, CREDIT CARD, IP ADDRESS, API KEY.
- `MemoryVault` (default, ephemeral) and `RedisVault` (optional, customer-owned).
- Deterministic token format `[PII:TYPE:8hexhash]` — same value always maps to the same token.
- Case-normalised deduplication — `john smith` / `John Smith` / `JOHN SMITH` all produce the same token.
- `MaskResult` with `.text`, `.entities`, `.has_pii`, and `.uncertain`.
- OpenAI `chat.completions` wrapper (`ArmosOpenAI`).
- Anthropic `messages` wrapper (`ArmosAnthropic`).
