"""
Armos detection accuracy benchmark.
Tests all supported PII entity types across 1000 samples each.
Outputs results to stdout and saves assets/accuracy.png.
"""
import random
import string
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from armos import Armos

random.seed(42)

# ---------------------------------------------------------------------------
# Sample data — names
# ---------------------------------------------------------------------------

FIRST_NAMES_MALE = [
    "Rahul", "Amit", "Vikas", "Rohit", "Sanjay", "Rajesh", "Suresh", "Arjun",
    "Karan", "Nikhil", "Pradeep", "Ravi", "Sunil", "Deepak", "Ashok", "Ramesh",
    "Manish", "Vikram", "Ajay", "Rakesh", "Naveen", "Mohan", "Girish", "Harish",
    "Krishna", "Santosh", "Ganesh", "Dinesh", "Mukesh", "Naresh", "Yogesh",
    "Hitesh", "Umesh", "Lokesh", "Mahesh", "Anil", "Vijay", "Vinod", "Pramod",
    "Arun", "Tarun", "Varun", "Karun", "Pawan", "Sachin", "Nitin",
]

FIRST_NAMES_FEMALE = [
    "Priya", "Neha", "Pooja", "Kavita", "Sunita", "Anita", "Rekha", "Meena",
    "Geeta", "Seema", "Anjali", "Deepa", "Divya", "Radha", "Laxmi", "Savita",
    "Usha", "Asha", "Nisha", "Ritu", "Sonia", "Sapna", "Pallavi", "Swati",
    "Sneha", "Shruti", "Preeti", "Archana", "Vandana", "Madhuri", "Namita",
    "Smita", "Amita", "Babita", "Kavya", "Tanvi", "Srishti", "Aditi", "Shweta",
    "Sonali", "Rupali", "Poonam", "Reena", "Veena", "Heena", "Meera", "Hema",
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Singh", "Kumar", "Mehta", "Joshi", "Shah",
    "Verma", "Mishra", "Yadav", "Tiwari", "Pandey", "Chauhan", "Malhotra",
    "Kapoor", "Agarwal", "Bansal", "Garg", "Mittal", "Bhat", "Nair", "Menon",
    "Pillai", "Iyer", "Rao", "Reddy", "Naidu", "Mukherjee", "Chatterjee",
    "Banerjee", "Ghosh", "Bose", "Sen", "Das", "Dey", "Roy", "Chakraborty",
    "Desai", "Patil", "Kulkarni", "Shinde", "More", "Jadhav", "Pawar", "Bhatt",
    "Trivedi", "Chaturvedi", "Dwivedi", "Upadhyay",
]

ALL_FIRST_NAMES = FIRST_NAMES_MALE + FIRST_NAMES_FEMALE

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "company.com", "hospital.org", "startup.in", "corp.co.in",
]

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def random_name():
    return f"{random.choice(ALL_FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_email():
    first = random.choice(ALL_FIRST_NAMES).lower()
    last = random.choice(LAST_NAMES).lower()
    sep = random.choice([".", "_", ""])
    num = random.choice(["", str(random.randint(1, 99))])
    domain = random.choice(EMAIL_DOMAINS)
    return f"{first}{sep}{last}{num}@{domain}"


def random_phone():
    first_digit = random.choice(["6", "7", "8", "9"])
    rest = "".join([str(random.randint(0, 9)) for _ in range(9)])
    digits = first_digit + rest
    return f"+91 {digits[:5]} {digits[5:]}"


def random_aadhaar():
    first = random.randint(2, 9)
    rest = [random.randint(0, 9) for _ in range(11)]
    d = [first] + rest
    return f"{d[0]}{d[1]}{d[2]}{d[3]} {d[4]}{d[5]}{d[6]}{d[7]} {d[8]}{d[9]}{d[10]}{d[11]}"


def random_pan():
    letters = string.ascii_uppercase
    return (
        "".join(random.choices(letters, k=5))
        + "".join(random.choices(string.digits, k=4))
        + random.choice(letters)
    )


def _luhn_checksum(digits):
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10


def random_card():
    prefix = random.choice(["4", "51", "52", "53", "54", "55", "34", "37"])
    length = 15 if prefix in ("34", "37") else 16
    digits = list(prefix)
    while len(digits) < length - 1:
        digits.append(str(random.randint(0, 9)))
    check = (10 - _luhn_checksum(digits + ["0"])) % 10
    digits.append(str(check))
    raw = "".join(digits)
    if length == 16:
        return f"{raw[:4]} {raw[4:8]} {raw[8:12]} {raw[12:]}"
    return f"{raw[:4]} {raw[4:10]} {raw[10:]}"


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def random_apikey():
    kind = random.choice(["openai", "aws", "github"])
    alnum = string.ascii_letters + string.digits
    if kind == "openai":
        return "sk-" + "".join(random.choices(alnum, k=48))
    elif kind == "aws":
        return "AKIA" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    else:
        return "ghp_" + "".join(random.choices(alnum, k=36))


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

NAME_TEMPLATES = [
    "Patient {} visited the clinic today.",
    "My name is {} and I need assistance.",
    "Please contact {} for further details.",
    "Account holder: {}.",
    "{} has submitted the application.",
]

EMAIL_TEMPLATES = [
    "Please reach out to {} for support.",
    "Send the report to {}.",
    "Contact email: {}.",
    "User registered with {}.",
    "Reply to {} with your query.",
]

PHONE_TEMPLATES = [
    "Call us at {}.",
    "Customer phone number: {}.",
    "Reach {} for immediate support.",
    "Primary contact: {}.",
    "Registered mobile: {}.",
]

AADHAAR_TEMPLATES = [
    "Aadhaar number: {}.",
    "My Aadhaar is {}.",
    "Aadhaar card: {} issued by UIDAI.",
    "KYC verified with Aadhaar {}.",
    "Please provide Aadhaar {} for verification.",
]

PAN_TEMPLATES = [
    "PAN card: {}.",
    "My PAN is {}.",
    "Tax filed under PAN {}.",
    "PAN number {} linked to this account.",
    "Please submit PAN {} for verification.",
]

CARD_TEMPLATES = [
    "Charged to card ending {}.",
    "Credit card number: {}.",
    "Payment made using {}.",
    "Card on file: {}.",
    "Transaction authorised for card {}.",
]

IP_TEMPLATES = [
    "Request received from IP {}.",
    "User logged in from {}.",
    "Access denied for IP {}.",
    "Origin IP: {}.",
    "Flagged activity from {}.",
]

APIKEY_TEMPLATES = [
    "API key: {}.",
    "Using token {}.",
    "Authenticate with {}.",
    "Set Authorization header to {}.",
    "Service called with key {}.",
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_test(label, generator, templates, entity_marker, n=1000):
    guard = Armos()
    detected = 0
    for _ in range(n):
        value = generator()
        text = random.choice(templates).format(value)
        result = guard.mask(text)
        if entity_marker in result.text:
            detected += 1
    rate = detected / n * 100
    print(f"{label:<10} {detected:>5}/{n}  ({rate:.1f}%)")
    return label, detected, rate


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

print("\n=== Armos Detection Accuracy (1000 samples each) ===\n")
print(f"{'Entity':<10} {'Detected':>10}  {'Rate':>8}")
print("-" * 35)

results = [
    run_test("NAME",    random_name,    NAME_TEMPLATES,    "[PII:NAME:"),
    run_test("EMAIL",   random_email,   EMAIL_TEMPLATES,   "[PII:EMAIL:"),
    run_test("PHONE",   random_phone,   PHONE_TEMPLATES,   "[PII:PHONE:"),
    run_test("AADHAAR", random_aadhaar, AADHAAR_TEMPLATES, "[PII:AADHAAR:"),
    run_test("PAN",     random_pan,     PAN_TEMPLATES,     "[PII:PAN:"),
    run_test("CARD",    random_card,    CARD_TEMPLATES,    "[PII:CARD:"),
    run_test("IP",      random_ip,      IP_TEMPLATES,      "[PII:IP:"),
    run_test("APIKEY",  random_apikey,  APIKEY_TEMPLATES,  "[PII:APIKEY:"),
]

print()

# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

labels = [r[0] for r in results]
rates  = [r[2] for r in results]
colors = ["#a1a1aa" if lbl == "NAME" else "#3b82f6" for lbl in labels]

fig, ax = plt.subplots(figsize=(11, 5))
fig.patch.set_facecolor("#0f0f0f")
ax.set_facecolor("#0f0f0f")

bars = ax.bar(labels, rates, color=colors, width=0.5)

for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            f"{rate:.1f}%", ha="center", va="bottom", color="#e4e4e7", fontsize=10)

ax.set_ylim(0, 115)
ax.set_ylabel("Detection rate (%)", color="#e4e4e7", fontsize=11)
ax.set_title("Armos — PII detection accuracy (1 000 samples per entity)", color="#ffffff", fontsize=13, pad=14)
ax.tick_params(colors="#a1a1aa")
ax.spines[:].set_color("#3f3f46")
ax.yaxis.label.set_color("#e4e4e7")
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, color="#e4e4e7", fontsize=10)
ax.grid(axis="y", color="#27272a", linewidth=0.8)
ax.axhline(y=100, color="#3f3f46", linewidth=0.8, linestyle="--")

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "assets", "accuracy.png")
plt.savefig(out, dpi=150, facecolor=fig.get_facecolor())
print(f"Chart saved → {os.path.abspath(out)}")
