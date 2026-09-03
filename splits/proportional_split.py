"""Buy if the sum of stated values covers the cost; split proportionally to
stated value."""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    total_stated = sum(stated for _, stated in offers)
    purchase = total_stated >= COST
    if not purchase:
        return False, {id_: 0.0 for id_, _ in offers}
    return True, {id_: COST * (stated / total_stated) for id_, stated in offers}
