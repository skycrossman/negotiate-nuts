"""Scoring: how much value negotiators get, and whether honesty pays off.

The headline metric is TRUTHFULNESS REGRET, a direct counterfactual test of
incentive compatibility. For each negotiator in a round, holding everyone
else's reports fixed, we sweep a grid of alternative reports and ask: how
much better could this agent have done than by reporting their true value?

  regret_i = max over reports r of u_i(r, others) - u_i(true_wtp, others)

where u_i = (true_wtp if purchase else 0) - payment. A split function under
which honesty is always a best response has regret 0 everywhere; the bigger
the regret, the more the mechanism rewards strategic misreporting.

We also keep secondary, correlational readouts (honesty <-> value correlation
and per-strategy averages). Beware their confounds: value contains true_wtp
directly, and clipping in negotiator.py makes high-true-value "overstate"
agents nearly honest, so treat regret as the metric that answers the real
question.
"""
from dataclasses import dataclass, field

from negotiator import MIN_WTP, MAX_WTP, Negotiator
from split_functions import COST

REGRET_EPSILON = 1e-9  # regret above this counts as "exploitable"


def score_round(
    negotiators: list[Negotiator], purchase: bool, payments: dict[int, float]
) -> dict[int, float]:
    """Return value received by each negotiator id for this round.

    Payments are subtracted even when no purchase happens, because some
    mechanisms (Clarke) tax agents who pivot the decision to "don't buy".
    """
    return {
        n.id: (n.true_wtp if purchase else 0.0) - payments.get(n.id, 0.0)
        for n in negotiators
    }


def truthfulness_regrets(
    negotiators: list[Negotiator], split_function, grid_step: int = 25
) -> dict[int, float]:
    """Per-agent regret of reporting truthfully, holding others' reports fixed.

    For each agent, every other agent keeps the stated_wtp they actually
    reported this round, and we compare the agent's utility from reporting
    true_wtp against the best utility achievable over a grid of alternative
    reports. Always >= 0; exactly 0 at every profile for a strategyproof
    mechanism.
    """
    base_offers = [(n.id, n.stated_wtp) for n in negotiators]
    grid = list(range(MIN_WTP, MAX_WTP + 1, grid_step))
    if grid[-1] != MAX_WTP:
        grid.append(MAX_WTP)

    regrets: dict[int, float] = {}
    for idx, agent in enumerate(negotiators):
        def utility(report: int) -> float:
            offers = list(base_offers)
            offers[idx] = (agent.id, report)
            purchase, payments = split_function(offers)
            gross = agent.true_wtp if purchase else 0.0
            return gross - payments.get(agent.id, 0.0)

        u_truth = utility(agent.true_wtp)
        best = max(utility(r) for r in grid)
        regrets[agent.id] = max(0.0, best - u_truth)
    return regrets


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std_err(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = _mean(values)
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return (var / n) ** 0.5


@dataclass
class SplitFunctionStats:
    name: str
    rounds: int = 0
    purchases: int = 0
    value_by_strategy: dict = field(default_factory=lambda: {
        "truthful": [], "overstate": [], "understate": [], "random": []
    })
    honesty_value_pairs: list = field(default_factory=list)  # (honesty, value)
    regrets: list = field(default_factory=list)
    ir_violations: int = 0  # agent-rounds where value < 0 (paid above true_wtp)
    agent_rounds: int = 0
    budget_surpluses: list = field(default_factory=list)  # per round

    def record_round(
        self,
        negotiators: list[Negotiator],
        purchase: bool,
        payments: dict[int, float],
        regrets: dict[int, float] | None = None,
    ) -> None:
        self.rounds += 1
        if purchase:
            self.purchases += 1
        self.budget_surpluses.append(
            sum(payments.values()) - (COST if purchase else 0.0)
        )
        values = score_round(negotiators, purchase, payments)
        for n in negotiators:
            v = values[n.id]
            self.agent_rounds += 1
            if v < -REGRET_EPSILON:
                self.ir_violations += 1
            self.value_by_strategy[n.strategy].append(v)
            honesty = -abs(n.stated_wtp - n.true_wtp)
            self.honesty_value_pairs.append((honesty, v))
        if regrets is not None:
            self.regrets.extend(regrets.values())

    @property
    def purchase_rate(self) -> float:
        return self.purchases / self.rounds if self.rounds else 0.0

    @property
    def all_values(self) -> list[float]:
        return [v for values in self.value_by_strategy.values() for v in values]

    @property
    def avg_value_per_negotiator(self) -> float:
        return _mean(self.all_values)

    def avg_value_for(self, strategy: str) -> float:
        return _mean(self.value_by_strategy[strategy])

    @property
    def mean_regret(self) -> float:
        return _mean(self.regrets)

    @property
    def max_regret(self) -> float:
        return max(self.regrets) if self.regrets else 0.0

    @property
    def exploitable_rate(self) -> float:
        """Fraction of sampled agent-rounds where some misreport beats truth."""
        if not self.regrets:
            return 0.0
        return sum(1 for r in self.regrets if r > REGRET_EPSILON) / len(self.regrets)

    @property
    def ir_violation_rate(self) -> float:
        return self.ir_violations / self.agent_rounds if self.agent_rounds else 0.0

    @property
    def honesty_value_correlation(self) -> float:
        return _pearson_correlation(self.honesty_value_pairs)

    def report(self) -> str:
        values = self.all_values
        lines = [
            f"== {self.name} ==",
            f"  rounds: {self.rounds}, purchase rate: {self.purchase_rate:.2%}",
            f"  avg value/negotiator: {_mean(values):.2f} (SE {_std_err(values):.2f})",
            "  truthfulness regret (0 = honesty is always a best response):",
            f"    mean: {self.mean_regret:.2f}, max: {self.max_regret:.2f}, "
            f"exploitable agent-rounds: {self.exploitable_rate:.2%} "
            f"({len(self.regrets)} sampled)",
            f"  forced losses (paid above true value): {self.ir_violation_rate:.2%} of agent-rounds",
            f"  avg budget surplus/round: {_mean(self.budget_surpluses):.2f}",
            f"  honesty <-> value correlation: {self.honesty_value_correlation:+.3f}"
            "  (secondary, confounded -- see module docstring)",
            "  avg value by strategy:",
        ]
        for strategy in ("truthful", "overstate", "understate", "random"):
            vals = self.value_by_strategy[strategy]
            lines.append(
                f"    {strategy:10s}: {_mean(vals):8.2f} (SE {_std_err(vals):.2f})"
            )
        return "\n".join(lines)


def _pearson_correlation(pairs: list[tuple[float, float]]) -> float:
    n = len(pairs)
    if n < 2:
        return 0.0
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    return cov / denom if denom else 0.0
