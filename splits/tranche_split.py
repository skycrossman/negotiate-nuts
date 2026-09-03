"""Buy if the sum of stated values covers the cost, then fill the cost in
tranches. Everyone would ideally split evenly, but no one pays more than they
stated: the lowest stater pays their stated value in full, and the rest split
what remains of the cost evenly among themselves -- repeating until every
remaining payer can cover an equal share of the remaining cost. (This is the
constrained-equal-awards rule; because we only buy when the stated values sum
to at least COST, no one is ever charged above their stated value.)"""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    total_stated = sum(stated for _, stated in offers)
    purchase = total_stated >= COST
    if not purchase:
        return False, {id_: 0.0 for id_, _ in offers}

    payments = {id_: 0.0 for id_, _ in offers}
    remaining_cost = float(COST)
    remaining = sorted(offers, key=lambda offer: offer[1])
    while remaining:
        share = remaining_cost / len(remaining)
        id_, stated = remaining[0]
        if stated >= share:
            for id_, _ in remaining:
                payments[id_] = share
            break
        payments[id_] = float(stated)
        remaining_cost -= stated
        remaining.pop(0)
    return True, payments
