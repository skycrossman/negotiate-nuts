import random

from negotiator import generate_negotiators
from scoring import SplitFunctionStats, truthfulness_regrets
from split_functions import validate_split_result


def run_simulation(
    split_functions: dict,
    num_rounds: int = 5000,
    seed: int | None = None,
    regret_every: int = 5,
    regret_grid_step: int = 25,
) -> dict[str, SplitFunctionStats]:
    """Run the same sequence of randomly generated rounds through every split
    function, so results are directly comparable.

    Truthfulness regret is expensive (a grid of counterfactual reports per
    agent), so it is computed on every `regret_every`-th round; the sampled
    rounds are the same for every split function.
    """
    rng = random.Random(seed)
    stats = {name: SplitFunctionStats(name=name) for name in split_functions}

    for round_idx in range(num_rounds):
        negotiators = generate_negotiators(rng)
        offers = [(n.id, n.stated_wtp) for n in negotiators]
        sample_regret = round_idx % regret_every == 0

        for name, split_function in split_functions.items():
            purchase, payments = split_function(offers)
            validate_split_result(offers, purchase, payments)
            regrets = (
                truthfulness_regrets(negotiators, split_function, regret_grid_step)
                if sample_regret
                else None
            )
            stats[name].record_round(negotiators, purchase, payments, regrets)

    return stats
