"""
Armos latency benchmark.
Measures mask() + demask() across text sizes for MemoryVault and RedisVault.
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

from armos import Armos

RUNS = 50
REDIS_URL = "redis://localhost:6379"

SAMPLES = {
    "Short\n(~20 tokens)": "Patient John Smith, email john@hospital.com.",
    "Medium\n(~60 tokens)": (
        "Dear Dr. Patel, patient Priya Sharma (Aadhaar 2345 6789 0123, PAN ABCDE1234F) "
        "called from +91 98765 43210 regarding her appointment on 12/04/1982."
    ),
    "Long\n(~150 tokens)": (
        "PATIENT RECORD — John Smith (DOB 15/06/1978), email john.smith@gmail.com, "
        "phone +91 98765 43210. Aadhaar: 2345 6789 0123. PAN: ABCDE1234F. "
        "Credit card ending 4111 1111 1111 1111. Referred by Dr. Anjali Mehta "
        "(anjali.mehta@apollo.com). Secondary contact: Jane Smith at jane@example.com, "
        "Aadhaar 9876 5432 1098. IP logged: 192.168.1.100. API key: sk-abc123xyz456."
    ),
}


def measure(guard, text, runs=RUNS):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = guard.mask(text)
        guard.demask(result.text)
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times), statistics.quantiles(times, n=20)[-1]  # p50, p95


def run():
    guard_mem = Armos()
    try:
        guard_redis = Armos(store="redis", redis_url=REDIS_URL)
        redis_available = True
    except Exception as e:
        print(f"Redis unavailable: {e}")
        redis_available = False

    labels = list(SAMPLES.keys())
    mem_p50, mem_p95 = [], []
    redis_p50, redis_p95 = [], []

    for label, text in SAMPLES.items():
        # warm up
        for _ in range(5):
            r = guard_mem.mask(text)
            guard_mem.demask(r.text)

        p50, p95 = measure(guard_mem, text)
        mem_p50.append(p50)
        mem_p95.append(p95)

        if redis_available:
            for _ in range(5):
                r = guard_redis.mask(text)
                guard_redis.demask(r.text)
            p50r, p95r = measure(guard_redis, text)
            redis_p50.append(p50r)
            redis_p95.append(p95r)

    print("\n=== Armos Latency Benchmark (mask + demask round-trip, PII text) ===")
    print(f"{'Text size':<22} {'Mem p50':>10} {'Mem p95':>10} {'Redis p50':>12} {'Redis p95':>12}")
    print("-" * 68)
    for i, label in enumerate(labels):
        clean_label = label.replace("\n", " ")
        rp50 = f"{redis_p50[i]:>11.1f}ms" if redis_available else "        n/a"
        rp95 = f"{redis_p95[i]:>11.1f}ms" if redis_available else "        n/a"
        print(f"{clean_label:<22} {mem_p50[i]:>9.1f}ms {mem_p95[i]:>9.1f}ms {rp50} {rp95}")

    # --- chart ---
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#0f0f0f")

    x = range(len(labels))
    w = 0.2

    bar_mem_p50   = ax.bar([i - 1.5*w for i in x], mem_p50,   width=w, color="#ffffff", label="Memory — p50")
    bar_mem_p95   = ax.bar([i - 0.5*w for i in x], mem_p95,   width=w, color="#a1a1aa", label="Memory — p95")

    if redis_available:
        bar_redis_p50 = ax.bar([i + 0.5*w for i in x], redis_p50, width=w, color="#3b82f6", label="Redis — p50")
        bar_redis_p95 = ax.bar([i + 1.5*w for i in x], redis_p95, width=w, color="#93c5fd", label="Redis — p95")
        all_bars = [bar_mem_p50, bar_mem_p95, bar_redis_p50, bar_redis_p95]
    else:
        all_bars = [bar_mem_p50, bar_mem_p95]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, color="#e4e4e7", fontsize=11)
    ax.set_ylabel("Latency (ms)", color="#e4e4e7", fontsize=11)
    ax.set_title("Armos — mask + demask round-trip latency (PII text)", color="#ffffff", fontsize=13, pad=14)
    ax.tick_params(colors="#a1a1aa")
    ax.spines[:].set_color("#3f3f46")
    ax.yaxis.label.set_color("#e4e4e7")
    ax.legend(framealpha=0, labelcolor="#e4e4e7", fontsize=10)
    ax.grid(axis="y", color="#27272a", linewidth=0.8)

    for bar_group in all_bars:
        for bar in bar_group:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3, f"{h:.0f}",
                    ha="center", va="bottom", color="#e4e4e7", fontsize=8)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "benchmark.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=150, facecolor=fig.get_facecolor())
    print(f"\nChart saved → {os.path.abspath(out)}")


if __name__ == "__main__":
    run()
