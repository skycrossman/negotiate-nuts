"""Equal cost-share VCG (Clarke pivot) mechanism.

Each agent's cost share is fixed at COST/n, so their net value for buying
is stated - COST/n. The group buys iff total net value >= 0 (equivalent to
sum of stated values >= COST). An agent is "pivotal" if the decision would
flip without their report; a pivotal agent pays an extra tax equal to the
net surplus the others lose because of them:

  - pivotal FOR buying (others alone would not buy): tax = -(others' net)
  - pivotal AGAINST buying (others alone would buy): tax = others' net,
    charged even though no purchase happens

This is the textbook dominant-strategy-incentive-compatible mechanism:
no agent can gain by misreporting, regardless of what others report.
Pivot taxes are burned, not redistributed (the classic VCG budget
imbalance), and the fixed equal share means it is NOT individually
rational -- a low-value agent can be forced into a loss.
"""
from split_functions import COST


def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
    n = len(offers)
    share = COST / n
    total_net = sum(stated - share for _, stated in offers)
    purchase = total_net >= 0

    payments: dict[int, float] = {}
    for id_, stated in offers:
        others_net = total_net - (stated - share)
        if purchase:
            pivot_tax = -others_net if others_net < 0 else 0.0
            payments[id_] = share + pivot_tax
        else:
            pivot_tax = others_net if others_net > 0 else 0.0
            payments[id_] = pivot_tax
    return purchase, payments
