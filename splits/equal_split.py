"""Buy if the sum of stated values covers the cost; split the cost evenly."""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    n = len(offers)
    total_stated = sum(stated for _, stated in offers)
    purchase = total_stated >= COST
    if not purchase:
        return False, {id_: 0.0 for id_, _ in offers}
    share = COST / n
    return True, {id_: share for id_, _ in offers}
