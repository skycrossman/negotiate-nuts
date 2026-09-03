"""Randomized acceptance: propose a split, then buy only with the probability
that caps the best-off negotiator's expected take at just under a fair share.

The proposed split charges each negotiator in proportion to their stated value
(so understating buys you a discount -- that discount is the "greedy demand"
this rule is built to neutralize; under an equal split nobody is ever treated
unfairly and the coin would always come up accept).

With n negotiators the fair share of the cost is f = COST / n, so a negotiator
who states s and is charged c takes s - c out of the deal where a fair split
would have left them s - f. If c >= f they are not over-taking and would accept
for certain. If c < f they are taking more than their share, and the purchase
happens only with probability

    p = (s - f - eps) / (s - c)

so their expected take is (s - f) - eps: a hair under fair, whatever they
demanded. `eps` grows with the size of the unfairness (EPS_BASE + EPS_SLOPE
times the amount of the fair share dodged), which makes a greedier proposal
strictly worse for its proposer rather than merely no better. The group's
acceptance probability is the smallest p over all negotiators -- the deal has
to clear the negotiator with the strongest objection -- and one uniform draw
below p accepts.

The coin is drawn deterministically from the offers, so the same offers always
give the same answer: rounds stay reproducible and every mechanism in the
comparison sees the same round. Note that this makes regret a noisy read on a
randomized mechanism -- the counterfactual sweep can find reports whose coin
happens to land on accept, which shows up as regret that is really variance.
"""
import hashlib

from split_functions import COST

EPS_BASE = 1.0    # flat tilt: deviating is never merely break-even
EPS_SLOPE = 0.1   # extra tilt per unit of fair share dodged


def _coin(offers: list[tuple[int, int]]) -> float:
    """A uniform draw on [0, 1) that is a deterministic function of the offers."""
    digest = hashlib.sha256(repr(sorted(offers)).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    no_purchase = {id_: 0.0 for id_, _ in offers}
    total_stated = sum(stated for _, stated in offers)
    if total_stated < COST:
        return False, no_purchase

    fair = COST / len(offers)
    payments = {id_: COST * (stated / total_stated) for id_, stated in offers}

    accept_prob = 1.0
    for id_, stated in offers:
        dodged = fair - payments[id_]
        if dodged <= 0:  # paying a fair share or more: no objection to answer
            continue
        eps = EPS_BASE + EPS_SLOPE * dodged
        take = stated - payments[id_]
        fair_take = stated - fair - eps
        p = 0.0 if fair_take <= 0 else min(1.0, fair_take / take)
        accept_prob = min(accept_prob, p)

    if _coin(offers) >= accept_prob:
        return False, no_purchase
    return True, payments
