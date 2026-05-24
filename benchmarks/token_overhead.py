"""
Measures token overhead introduced by armos masking tokens.
Uses cl100k_base (GPT-4) tokenization.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import tiktoken
from armos import Armos

enc = tiktoken.get_encoding("cl100k_base")

def tokens(text):
    return len(enc.encode(text))

SAMPLES = [
    ("NAME",    "John Smith"),
    ("NAME",    "Priya Sharma"),
    ("EMAIL",   "john@example.com"),
    ("EMAIL",   "priya.sharma@healthtech.in"),
    ("AADHAAR", "2345 6789 0123"),
    ("PAN",     "ABCDE1234F"),
    ("PHONE",   "+91 98765 43210"),
    ("CARD",    "4111 1111 1111 1111"),
    ("IP",      "192.168.1.100"),
    ("APIKEY",  "sk-abc123xyz456def789"),
]

guard = Armos()

print(f"\n{'Entity':<10} {'Original value':<30} {'Orig tokens':>12} {'Masked tokens':>14} {'Overhead':>10}")
print("-" * 80)

totals_orig, totals_masked = [], []
for entity_type, value in SAMPLES:
    result = guard.mask(value)
    masked_text = result.text

    orig_t = tokens(value)
    masked_t = tokens(masked_text)
    overhead = masked_t - orig_t

    totals_orig.append(orig_t)
    totals_masked.append(masked_t)
    print(f"{entity_type:<10} {value:<30} {orig_t:>12} {masked_t:>14} {overhead:>+10}")

print("-" * 80)
print(f"{'Average':<10} {'':<30} {sum(totals_orig)/len(totals_orig):>12.1f} {sum(totals_masked)/len(totals_masked):>14.1f} {(sum(totals_masked)-sum(totals_orig))/len(totals_orig):>+10.1f}")

# Also show a full message example
msg = "Patient John Smith, Aadhaar 2345 6789 0123, email john@hospital.com, PAN ABCDE1234F"
result = guard.mask(msg)

print(f"\n--- Full message example ---")
print(f"Original  ({tokens(msg):>3} tokens): {msg}")
print(f"Masked    ({tokens(result.text):>3} tokens): {result.text}")
print(f"Overhead: +{tokens(result.text) - tokens(msg)} tokens")
