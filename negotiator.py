"""Negotiator generation."""
from dataclasses import dataclass
import random

MIN_WTP = 1
MAX_WTP = 1000

# How far a dishonest negotiator's stated value can drift from their true value.
MAX_MISREPORT = 300


@dataclass
class Negotiator:
    id: int
    true_wtp: int
    stated_wtp: int
    strategy: str  # "truthful", "overstate", "understate", "random" -- for analysis only


def _clip(value: int) -> int:
    return max(MIN_WTP, min(MAX_WTP, value))


def make_negotiator(id_: int, rng: random.Random) -> Negotiator:
    true_wtp = rng.randint(MIN_WTP, MAX_WTP)
    strategy = rng.choice(["truthful", "overstate", "understate", "random"])

    if strategy == "truthful":
        stated_wtp = true_wtp
    elif strategy == "overstate":
        stated_wtp = _clip(true_wtp + rng.randint(1, MAX_MISREPORT))
    elif strategy == "understate":
        stated_wtp = _clip(true_wtp - rng.randint(1, MAX_MISREPORT))
    else:  # random
        stated_wtp = rng.randint(MIN_WTP, MAX_WTP)

    return Negotiator(id=id_, true_wtp=true_wtp, stated_wtp=stated_wtp, strategy=strategy)


def generate_negotiators(rng: random.Random, count: int | None = None) -> list[Negotiator]:
    """A random collection of 2 to 10 Negotiators."""
    if count is None:
        count = rng.randint(2, 10)
    return [make_negotiator(i, rng) for i in range(count)]
