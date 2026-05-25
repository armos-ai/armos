# Troubleshooting

Common issues and fixes.

---

## ImportError: No module named 'redis'

**Symptom**
```
ImportError: Redis support requires the redis package.
```

**Fix**
You're using `store="redis"` but the redis package isn't installed.
```bash
pip install armos[redis]
```

---

## spaCy model not found

**Symptom**
```
OSError: [E050] Can't find model 'en_core_web_lg'.
```

**Fix**
Download the spaCy model on first use:
```bash
python -m spacy download en_core_web_lg
```

---

## PII not being detected

**Symptom**
Names, emails, or other PII pass through to the LLM unmasked.

**Possible causes**

- **Indian names** — `en_core_web_lg` has lower recall for Indian names than Western names. This is a known limitation. Aadhaar and PAN are detected reliably via regex.
- **Short or ambiguous text** — Presidio needs enough context to be confident. A bare email address like `john@test.com` alone may have lower confidence than `Email john@test.com for support`.
- **Uncommon entity type** — check [what gets detected](README.md#what-gets-detected). Not all PII types are supported.

---

## LLM treats tokens as placeholders

**Symptom**
The LLM response contains `[Employee Name]` or similar instead of using the `[PII:NAME:xxxx]` token.

**Fix**
This was a bug in versions before 0.1.5. Upgrade:
```bash
pip install --upgrade armos
```

From 0.1.5 onwards, armos automatically injects a system hint telling the LLM to reproduce tokens verbatim.

---

## Real values not restored in the response

**Symptom**
The LLM response still contains `[PII:NAME:xxxx]` tokens instead of real values.

**Possible causes**

- **Vault cleared between calls** — if you create a new `Armos()` instance per request, the vault is empty and tokens can't be de-masked. Reuse the same `ArmosOpenAI` / `ArmosAnthropic` instance across requests, or use Redis for persistence.
- **Token not in vault** — tokens from a previous process or a different instance can't be de-masked. Use Redis if you need cross-process persistence.

---

## Redis connection error

**Symptom**
```
redis.exceptions.ConnectionError: Error connecting to redis://localhost:6379
```

**Fix**
Make sure your Redis server is running:
```bash
redis-server
```
Then verify:
```bash
redis-cli ping  # should return PONG
```

---

## store="redis" raises ValueError: redis_url is required

**Symptom**
```
ValueError: redis_url is required when store='redis'.
```

**Fix**
Pass the `redis_url` argument explicitly:
```python
# Wrong
client = ArmosOpenAI(OpenAI(), store="redis")

# Right
client = ArmosOpenAI(OpenAI(), store="redis", redis_url="redis://localhost:6379")
```

---

## Streaming or async not working

Streaming (`stream=True`) and async clients (`AsyncOpenAI`, `AsyncAnthropic`) are not yet supported. They pass through without masking. This is a known limitation — planned for a future release.

---

## Still stuck?

Open an issue: [github.com/armos-ai/armos-python/issues](https://github.com/armos-ai/armos-python/issues)
