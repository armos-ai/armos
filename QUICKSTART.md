# Armos Quickstart

Get up and running in 5 minutes.

## 1. Install

```bash
pip install armos
python -m spacy download en_core_web_lg
```

## 2. Pick your SDK

### OpenAI

```python
from openai import OpenAI
from armos import ArmosOpenAI

client = ArmosOpenAI(OpenAI())

# Chat completions
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarise case for patient John Smith, Aadhaar 2345 6789 0123"}]
)
print(response.choices[0].message.content)  # real values restored

# Responses API
response = client.responses.create(
    model="gpt-4o",
    input="Patient John Smith, email john@hospital.com — write a one-line summary."
)
print(response.output[0].content[0].text)  # real values restored

# Embeddings
result = client.embeddings.create(
    model="text-embedding-3-small",
    input="John Smith, john@hospital.com"
)
# PII masked before sending — response is vectors as usual
```

### Anthropic

```python
from anthropic import Anthropic
from armos import ArmosAnthropic

client = ArmosAnthropic(Anthropic())

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Patient John Smith, PAN ABCDE1234F — summarise."}]
)
print(message.content[0].text)  # real values restored
```

## 3. Use standalone (any LLM or framework)

```python
from armos import Armos

guard = Armos()

result = guard.mask("Patient John Smith, email john@hospital.com, Aadhaar 2345 6789 0123")
print(result.text)      # masked text to send to LLM
print(result.has_pii)   # True
print(result.entities)  # list of detected entity types

restored = guard.demask(result.text)
print(restored)         # original text restored
```

## 4. Persist tokens across requests with Redis

```bash
pip install armos[redis]
```

```python
client = ArmosOpenAI(OpenAI(), store="redis", redis_url="redis://localhost:6379")

# Custom TTL (default: 24 hours)
client = ArmosOpenAI(OpenAI(), store="redis", redis_url="redis://localhost:6379", vault_ttl=3600)
```

## What gets detected

| Entity | Example |
|--------|---------|
| Person name | John Smith |
| Email | john@hospital.com |
| Phone | +91 98765 43210 |
| Aadhaar | 2345 6789 0123 |
| PAN | ABCDE1234F |
| Credit card | 4111 1111 1111 1111 |
| IP address | 192.168.1.100 |
| API keys | sk-abc123… / AKIA… / ghp_… |

## Next steps

- Full documentation: [README](README.md)
- Known limitations: [README — Known limitations](README.md#known-limitations)
- Issues: [github.com/armos-ai/armos-python/issues](https://github.com/armos-ai/armos-python/issues)
