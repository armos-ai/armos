"""
Armos latency benchmark.
Measures mask() + demask() across text sizes and PII densities.
Outputs assets/benchmark.png for the README.
"""
import time
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from armos import Armos

RUNS = 50

SAMPLES = {
    "Short\n(~20 tokens)": (
        "Patient John Smith, email john@hospital.com.",
        "The weather is nice today in Mumbai.",
    ),
    "Medium\n(~60 tokens)": (
        "Dear Dr. Patel, patient Priya Sharma (Aadhaar 2345 6789 0123, PAN ABCDE1234F) "
        "called from +91 98765 43210 regarding her appointment on 12/04/1982.",
        "The quarterly report shows strong growth across all three business units. "
        "Revenue increased by 23% compared to the previous year with no anomalies detected.",
    ),
    "Long\n(~150 tokens)": (
        "PATIENT RECORD — John Smith (DOB 15/06/1978), email john.smith@gmail.com, "
        "phone +91 98765 43210. Aadhaar: 2345 6789 0123. PAN: ABCDE1234F. "
        "Credit card ending 4111 1111 1111 1111. Referred by Dr. Anjali Mehta "
        "(anjali.mehta@apollo.com). Secondary contact: Jane Smith at jane@example.com, "
        "Aadhaar 9876 5432 1098. IP logged: 192.168.1.100. API key: sk-abc123xyz456.",
        "The engineering team completed the migration of all three microservices to the "
        "new Kubernetes cluster. Deployment pipelines were updated and all integration "
        "tests passed. The infrastructure team confirmed that auto-scaling policies are "
        "in place and the monitoring dashboards have been updated to reflect the new "
        "service topology. No regressions were observed during the rollout window.",
    ),
}


def measure(fn, runs=RUNS):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times), statistics.quantiles(times, n=20)[-1]  # p50, p95


def run():
    guard_pii = Armos()
    guard_clean = Armos()

    labels = list(SAMPLES.keys())
    pii_p50, pii_p95 = [], []
    clean_p50, clean_p95 = [], []

    for label, (pii_text, clean_text) in SAMPLES.items():
        # warm up
        for _ in range(5):
            r = guard_pii.mask(pii_text)
            guard_pii.demask(r.text)

        p50, p95 = measure(lambda t=pii_text: (lambda r: guard_pii.demask(r.text))(guard_pii.mask(t)))
        pii_p50.append(p50)
        pii_p95.append(p95)

        p50c, p95c = measure(lambda t=clean_text: (lambda r: guard_clean.demask(r.text))(guard_clean.mask(t)))
        clean_p50.append(p50c)
        clean_p95.append(p95c)

    print("\n=== Armos Latency Benchmark (mask + demask round-trip) ===")
    print(f"{'Text size':<22} {'PII p50':>10} {'PII p95':>10} {'Clean p50':>12} {'Clean p95':>12}")
    print("-" * 68)
    for i, label in enumerate(labels):
        clean_label = label.replace("\n", " ")
        print(f"{clean_label:<22} {pii_p50[i]:>9.1f}ms {pii_p95[i]:>9.1f}ms {clean_p50[i]:>11.1f}ms {clean_p95[i]:>11.1f}ms")

    # --- chart ---
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#0f0f0f")

    x = range(len(labels))
    w = 0.2

    colors = {"pii_p50": "#ffffff", "pii_p95": "#a1a1aa", "clean_p50": "#3b82f6", "clean_p95": "#93c5fd"}

    bars = [
        ax.bar([i - 1.5*w for i in x], pii_p50,   width=w, color=colors["pii_p50"],  label="PII text — p50"),
        ax.bar([i - 0.5*w for i in x], pii_p95,   width=w, color=colors["pii_p95"],  label="PII text — p95"),
        ax.bar([i + 0.5*w for i in x], clean_p50, width=w, color=colors["clean_p50"], label="Clean text — p50"),
        ax.bar([i + 1.5*w for i in x], clean_p95, width=w, color=colors["clean_p95"], label="Clean text — p95"),
    ]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, color="#e4e4e7", fontsize=11)
    ax.set_ylabel("Latency (ms)", color="#e4e4e7", fontsize=11)
    ax.set_title("Armos — mask + demask round-trip latency", color="#ffffff", fontsize=13, pad=14)
    ax.tick_params(colors="#a1a1aa")
    ax.spines[:].set_color("#3f3f46")
    ax.yaxis.label.set_color("#e4e4e7")
    ax.legend(framealpha=0, labelcolor="#e4e4e7", fontsize=10)
    ax.grid(axis="y", color="#27272a", linewidth=0.8)

    # value labels on bars
    for bar_group in bars:
        for bar in bar_group:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f"{h:.0f}",
                    ha="center", va="bottom", color="#e4e4e7", fontsize=8)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "benchmark.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=150, facecolor=fig.get_facecolor())
    print(f"\nChart saved → {os.path.abspath(out)}")


if __name__ == "__main__":
    run()
