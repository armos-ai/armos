"""
Armos detection accuracy benchmark.
Tests Indian names, Aadhaar, and PAN detection rates across 1000 samples each.
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
# Sample data
# ---------------------------------------------------------------------------

FIRST_NAMES_MALE = [
    "Rahul", "Amit", "Vikas", "Rohit", "Sanjay", "Rajesh", "Suresh", "Arjun",
    "Karan", "Nikhil", "Pradeep", "Ravi", "Sunil", "Deepak", "Ashok", "Ramesh",
    "Manish", "Vikram", "Ajay", "Rakesh", "Naveen", "Mohan", "Girish", "Harish",
    "Krishna", "Santosh", "Ganesh", "Dinesh", "Mukesh", "Naresh", "Yogesh",
    "Hitesh", "Umesh", "Lokesh", "Mahesh", "Anil", "Vijay", "Vinod", "Pramod",
    "Arun", "Tarun", "Varun", "Karun", "Pawan", "Sachin", "Sachin", "Nitin",
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


def random_name():
    return f"{random.choice(ALL_FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_aadhaar():
    first = random.randint(2, 9)
    rest = [random.randint(0, 9) for _ in range(11)]
    digits = [first] + rest
    return f"{digits[0]}{digits[1]}{digits[2]}{digits[3]} {digits[4]}{digits[5]}{digits[6]}{digits[7]} {digits[8]}{digits[9]}{digits[10]}{digits[11]}"


def random_pan():
    letters = string.ascii_uppercase
    pan = (
        "".join(random.choices(letters, k=5))
        + "".join(random.choices(string.digits, k=4))
        + random.choice(letters)
    )
    return pan


# ---------------------------------------------------------------------------
# Test contexts — same entity in different sentence structures
# ---------------------------------------------------------------------------

NAME_TEMPLATES = [
    "Patient {} visited the clinic today.",
    "My name is {} and I need assistance.",
    "Please contact {} for further details.",
    "Account holder: {}.",
    "{} has submitted the application.",
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


def run_test(label, generator, templates, entity_marker, n=1000):
    guard = Armos()
    detected = 0
    for _ in range(n):
        value = generator()
        template = random.choice(templates)
        text = template.format(value)
        result = guard.mask(text)
        if entity_marker in result.text:
            detected += 1
    rate = detected / n * 100
    print(f"{label:<12} {detected:>5}/{n}  ({rate:.1f}%)")
    return rate


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

print("\n=== Armos Detection Accuracy (1000 samples each) ===\n")
print(f"{'Entity':<12} {'Detected':>10}  {'Rate':>8}")
print("-" * 35)

name_rate     = run_test("NAME",    random_name,     NAME_TEMPLATES,    "[PII:NAME:")
aadhaar_rate  = run_test("AADHAAR", random_aadhaar,  AADHAAR_TEMPLATES, "[PII:AADHAAR:")
pan_rate      = run_test("PAN",     random_pan,       PAN_TEMPLATES,     "[PII:PAN:")

print()

# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(7, 4.5))
fig.patch.set_facecolor("#0f0f0f")
ax.set_facecolor("#0f0f0f")

labels = ["Indian Names\n(NER)", "Aadhaar\n(Regex)", "PAN\n(Regex)"]
rates  = [name_rate, aadhaar_rate, pan_rate]
colors = ["#a1a1aa", "#3b82f6", "#3b82f6"]

bars = ax.bar(labels, rates, color=colors, width=0.4)

for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            f"{rate:.1f}%", ha="center", va="bottom", color="#e4e4e7", fontsize=12)

ax.set_ylim(0, 115)
ax.set_ylabel("Detection rate (%)", color="#e4e4e7", fontsize=11)
ax.set_title("Armos — Indian PII detection accuracy (1 000 samples)", color="#ffffff", fontsize=13, pad=14)
ax.tick_params(colors="#a1a1aa")
ax.spines[:].set_color("#3f3f46")
ax.yaxis.label.set_color("#e4e4e7")
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, color="#e4e4e7", fontsize=11)
ax.grid(axis="y", color="#27272a", linewidth=0.8)
ax.axhline(y=100, color="#3f3f46", linewidth=0.8, linestyle="--")

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "assets", "accuracy.png")
plt.savefig(out, dpi=150, facecolor=fig.get_facecolor())
print(f"Chart saved → {os.path.abspath(out)}")
