from simulator import run_simulation
from split_functions import load_split_functions


def print_comparison(stats: dict) -> None:
    """Side-by-side summary, ranked by mean truthfulness regret (lower = better
    for honesty)."""
    header = (
        f"{'split function':<24} {'mean regret':>11} {'exploitable':>11} "
        f"{'forced loss':>11} {'avg value':>10} {'purchase':>9}"
    )
    print(header)
    print("-" * len(header))
    for s in sorted(stats.values(), key=lambda s: s.mean_regret):
        print(
            f"{s.name:<24} {s.mean_regret:>11.2f} {s.exploitable_rate:>10.2%} "
            f"{s.ir_violation_rate:>10.2%} {s.avg_value_per_negotiator:>10.2f} "
            f"{s.purchase_rate:>8.2%}"
        )
    print()
    print("mean regret / exploitable: how much (and how often) misreporting")
    print("beats honesty -- 0 means honesty is always a best response.")


def main():
    split_functions = load_split_functions()
    stats = run_simulation(split_functions, num_rounds=5000, seed=42)
    for name in split_functions:
        print(stats[name].report())
        print()
    print_comparison(stats)


if __name__ == "__main__":
    main()
