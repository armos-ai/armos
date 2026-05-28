"""
Address detection accuracy benchmark.
500 US addresses + 500 Indian addresses across realistic sub-types.
Outputs a per-category breakdown to show exactly where detection fails.

Run:
    python3 benchmarks/address_benchmark.py
"""
import random
import string
import sys
import os
import collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from armos import Armos

random.seed(42)

# ── US data ──────────────────────────────────────────────────────────────────

US_STREET_NAMES = [
    "Main", "Oak", "Maple", "Cedar", "Elm", "Pine", "Walnut", "Willow",
    "Washington", "Lincoln", "Jefferson", "Adams", "Jackson", "Madison",
    "Park", "Lake", "Hill", "River", "Spring", "Forest", "Meadow", "Valley",
    "Church", "School", "Mill", "Bridge", "College", "Market", "Union",
    "Center", "High", "North", "South", "East", "West", "New", "Old",
    "First", "Second", "Third", "Fourth", "Fifth",
]

US_SUFFIXES = [
    "Street", "St", "Avenue", "Ave", "Road", "Rd", "Boulevard", "Blvd",
    "Drive", "Dr", "Lane", "Ln", "Court", "Ct", "Place", "Pl", "Way",
    "Circle", "Cir", "Terrace", "Ter", "Trail", "Trl", "Parkway", "Pkwy",
]

US_CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
    "Fort Worth", "Columbus", "Charlotte", "Indianapolis", "San Francisco",
    "Seattle", "Denver", "Nashville", "Boston", "Portland", "Las Vegas",
    "Memphis", "Atlanta", "Miami", "Minneapolis", "Tucson", "Albuquerque",
]

US_STATES = [
    "NY", "CA", "IL", "TX", "AZ", "PA", "FL", "OH", "NC", "IN",
    "WA", "CO", "TN", "MA", "OR", "NV", "TN", "GA", "MN", "AZ",
]

# ── Indian data ───────────────────────────────────────────────────────────────

IN_BUILDING_TYPES = ["Flat", "House", "Door No.", "H. No.", "Plot No.", "Apartment", "Apt"]
IN_UNIT_PREFIXES  = ["", "A-", "B-", "C-", "D-", "Block "]

IN_SOCIETIES = [
    "Green Valley Apartments", "Prestige Towers", "Brigade Gateway",
    "Sobha Indraprastha", "DLF City", "Vatika Township", "Unitech Residency",
    "Ansal Plaza", "Parsvnath Exotica", "Omaxe Heights",
]

IN_STREETS_WITH_SUFFIX = [
    "MG Road", "Linking Road", "SV Road", "LBS Marg", "Patel Nagar Road",
    "Ring Road", "Outer Ring Road", "NH 48", "Bellary Road", "Old Airport Road",
    "Sarjapur Road", "Hosur Road", "Bannerghatta Road", "Mysore Road",
    "Tumkur Road", "Pune-Mumbai Highway",
]

IN_LOCALITIES = [
    "Koramangala", "Indiranagar", "Jayanagar", "Whitefield", "Malleswaram",
    "HSR Layout", "BTM Layout", "Electronic City", "Marathahalli",
    "Andheri West", "Bandra", "Juhu", "Powai", "Goregaon",
    "Salt Lake", "New Town", "Ballygunge", "Alipore",
    "Anna Nagar", "T Nagar", "Adyar", "Velachery", "Mylapore",
    "Sector 12", "Sector 18", "Sector 29", "Sector 62",
    "Nariman Point", "Lower Parel", "BKC",
]

IN_CITIES = [
    "Bangalore", "Mumbai", "Delhi", "Chennai", "Kolkata", "Hyderabad",
    "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Noida",
    "Gurgaon", "Ghaziabad",
]


# ── Generators ────────────────────────────────────────────────────────────────

def us_full_address():
    """123 Oak Avenue, Chicago, IL 60601"""
    num    = random.randint(1, 9999)
    street = random.choice(US_STREET_NAMES)
    suffix = random.choice(US_SUFFIXES)
    city   = random.choice(US_CITIES)
    state  = random.choice(US_STATES)
    zip_   = f"{random.randint(10000, 99999):05d}"
    return f"{num} {street} {suffix}, {city}, {state} {zip_}"


def us_street_only():
    """456 Elm Drive"""
    num    = random.randint(1, 9999)
    street = random.choice(US_STREET_NAMES)
    suffix = random.choice(US_SUFFIXES)
    return f"{num} {street} {suffix}"


def us_with_apt():
    """789 Main St, Apt 3B, Boston, MA 02101"""
    base  = us_full_address()
    apt   = f"Apt {random.randint(1,20)}{random.choice(list('ABCDE'))}"
    parts = base.split(",", 1)
    return f"{parts[0]}, {apt},{parts[1]}"


def us_po_box():
    """P.O. Box 1234, Dallas, TX 75201"""
    city  = random.choice(US_CITIES)
    state = random.choice(US_STATES)
    zip_  = f"{random.randint(10000, 99999):05d}"
    box   = random.randint(100, 99999)
    fmt   = random.choice(["P.O. Box", "PO Box", "P.O Box"])
    return f"{fmt} {box}, {city}, {state} {zip_}"


def indian_flat():
    """Flat 4B, Green Valley Apartments, Koramangala, Bangalore 560034"""
    btype  = random.choice(["Flat", "Apartment", "Apt"])
    unit   = f"{random.choice(IN_UNIT_PREFIXES)}{random.randint(1,50)}{random.choice(list('ABCDE'))}"
    soc    = random.choice(IN_SOCIETIES)
    loc    = random.choice(IN_LOCALITIES)
    city   = random.choice(IN_CITIES)
    pin    = f"{random.randint(110001, 700099):06d}"
    return f"{btype} {unit}, {soc}, {loc}, {city} {pin}"


def indian_house():
    """House 23, MG Road, Bangalore 560001"""
    btype  = random.choice(["House", "H. No.", "Door No."])
    num    = f"{random.randint(1, 999)}{random.choice(['', 'A', 'B', '/1', '/2'])}"
    street = random.choice(IN_STREETS_WITH_SUFFIX)
    city   = random.choice(IN_CITIES)
    pin    = f"{random.randint(110001, 700099):06d}"
    return f"{btype} {num}, {street}, {city} {pin}"


def indian_plot():
    """Plot No. 45, Sector 12, Gurgaon 122001"""
    num  = random.randint(1, 500)
    loc  = random.choice(IN_LOCALITIES)
    city = random.choice(IN_CITIES)
    pin  = f"{random.randint(110001, 700099):06d}"
    return f"Plot No. {num}, {loc}, {city} {pin}"


def indian_named_location():
    """10 Nariman Point, Mumbai  (no standard suffix — hard case)"""
    num  = random.randint(1, 200)
    loc  = random.choice(IN_LOCALITIES)
    city = random.choice(IN_CITIES)
    return f"{num} {loc}, {city}"


# ── Templates ─────────────────────────────────────────────────────────────────

ADDRESS_TEMPLATES = [
    "Please ship the order to {}.",
    "Customer address on file: {}.",
    "Billing address: {}.",
    "Delivery to {}.",
    "Mailing address: {}.",
    "The patient resides at {}.",
    "Employee residence: {}.",
    "Send the parcel to {}.",
    "Office address: {}.",
    "Registered address is {}.",
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_category(label, generator, n=500):
    guard  = Armos()
    hits   = 0
    misses = []

    for _ in range(n):
        value    = generator()
        template = random.choice(ADDRESS_TEMPLATES)
        text     = template.format(value)
        result   = guard.mask(text)

        if "[PII:ADDRESS:" in result.text:
            hits += 1
        else:
            misses.append(value)

    rate = hits / n * 100
    return label, hits, n, rate, misses


# ── Main ──────────────────────────────────────────────────────────────────────

CATEGORIES = [
    # label                   generator              region
    ("US — full address",     us_full_address,       "US"),
    ("US — street only",      us_street_only,        "US"),
    ("US — with apt",         us_with_apt,           "US"),
    ("US — P.O. Box",         us_po_box,             "US"),
    ("IN — flat/apartment",   indian_flat,           "India"),
    ("IN — house/door",       indian_house,          "India"),
    ("IN — plot",             indian_plot,           "India"),
    ("IN — named location",   indian_named_location, "India"),
]

print("\n=== Address Detection Benchmark (500 samples per category) ===\n")
print(f"{'Category':<26}  {'Detected':>10}  {'Rate':>7}")
print("-" * 50)

results = []
for label, gen, region in CATEGORIES:
    label_r, hits, n, rate, misses = run_category(label, gen)
    results.append((label, hits, n, rate, region, misses))
    bar = "█" * int(rate / 5)
    print(f"{label:<26}  {hits:>4}/{n}    {rate:>5.1f}%  {bar}")

# Per-region summary
print()
for region in ["US", "India"]:
    region_results = [(h, n) for l, h, n, r, reg, _ in results if reg == region]
    total_hits  = sum(h for h, n in region_results)
    total_samps = sum(n for h, n in region_results)
    print(f"  {region} overall: {total_hits}/{total_samps}  ({total_hits/total_samps*100:.1f}%)")

# Miss examples
print()
print("── Sample misses (up to 5 per category) ──────────────────────")
for label, hits, n, rate, region, misses in results:
    if misses:
        print(f"\n  {label}  ({len(misses)} missed):")
        for m in misses[:5]:
            print(f"    · {m}")

# ── Chart ─────────────────────────────────────────────────────────────────────

labels = [r[0] for r in results]
rates  = [r[3] for r in results]
colors = ["#3b82f6" if r[4] == "US" else "#22c55e" for r in results]

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor("#0f0f0f")
ax.set_facecolor("#0f0f0f")

bars = ax.bar(range(len(labels)), rates, color=colors, width=0.55)

for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            f"{rate:.0f}%", ha="center", va="bottom", color="#e4e4e7", fontsize=9)

ax.set_ylim(0, 115)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=18, ha="right", color="#e4e4e7", fontsize=9)
ax.set_ylabel("Detection rate (%)", color="#e4e4e7", fontsize=11)
ax.set_title("Armos — Address detection accuracy (500 samples per category)",
             color="#ffffff", fontsize=12, pad=14)
ax.tick_params(colors="#a1a1aa")
ax.spines[:].set_color("#3f3f46")
ax.grid(axis="y", color="#27272a", linewidth=0.8)
ax.axhline(y=100, color="#3f3f46", linewidth=0.8, linestyle="--")

from matplotlib.patches import Patch
legend = [Patch(color="#3b82f6", label="USA"), Patch(color="#22c55e", label="India")]
ax.legend(handles=legend, facecolor="#1a1a1a", edgecolor="#3f3f46",
          labelcolor="#e4e4e7", fontsize=9)

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "..", "assets", "address_accuracy.png")
plt.savefig(out, dpi=150, facecolor=fig.get_facecolor())
print(f"\nChart saved → {os.path.abspath(out)}")
