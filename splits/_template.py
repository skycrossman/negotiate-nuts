"""Template for a new split function. Copy this file, give it a name that
doesn't start with an underscore (the filename becomes the function's name in
reports), and fill in `split`.

You receive ONLY (id, stated_wtp) pairs -- never anyone's true value. Return
(purchase?, {id: payment}). The contract, checked every simulated round:
one payment entry per offered id, payments >= 0, and if purchase is True the
payments must total at least COST.
"""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    total_stated = sum(stated for _, stated in offers)
    purchase = total_stated >= COST
    if not purchase:
        return False, {id_: 0.0 for id_, _ in offers}
    # ... decide who pays what ...
    share = COST / len(offers)
    return True, {id_: share for id_, _ in offers}
