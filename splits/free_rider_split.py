"""Buy if the sum of stated values covers the cost. The cost is split
equally among the agents who can afford the resulting share by their own
stated value; anyone whose stated value falls below the equal share among
the remaining payers is excused entirely and free-rides. If exclusions
would leave nobody willing to pay, the last non-empty payer set covers the
cost anyway (possibly paying above their stated values)."""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    total_stated = sum(stated for _, stated in offers)
    purchase = total_stated >= COST
    if not purchase:
        return False, {id_: 0.0 for id_, _ in offers}

    payers = list(offers)
    while True:
        share = COST / len(payers)
        staying = [(id_, stated) for id_, stated in payers if stated >= share]
        if len(staying) == len(payers) or not staying:
            break
        payers = staying

    share = COST / len(payers)
    payments = {id_: 0.0 for id_, _ in offers}
    for id_, _ in payers:
        payments[id_] = share
    return True, payments
