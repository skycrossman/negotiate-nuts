# Split Function Testbed

A simulation harness for testing **split functions** — mechanisms that decide
whether a group of negotiators jointly buys something and how the cost is
divided — to find out which mechanisms make it in each negotiator's own
interest to honestly state their true value.

The scenario: a group of 2–10 negotiators considers a shared purchase with a
fixed cost (`COST = 500`). Each negotiator has a private *true willingness to
pay* (`true_wtp`, 1–1000) but reports a possibly-dishonest *stated* value. The
split function sees only the stated values and must decide whether to buy and
who pays what. The question we score: **could any negotiator have done better
by lying?**

## Quick start

```
python main.py                        # run the simulation, print reports + ranking
python -m unittest test_negotiation   # run the tests
```

## 1. Writing a split function

Split functions live in `splits/`, one per `.py` file. To add one, drop a file
into that directory (any name not starting with `_`; the filename becomes the
mechanism's name in reports) that defines:

```python
def split(offers: list[tuple[int, int]]) -> tuple[bool, dict[int, float]]:
```

**Input** — `offers`: a list of `(id, stated_wtp)` pairs, one per negotiator.
You only ever see *stated* values, never anyone's true willingness to pay. The
fixed cost is available as `from split_functions import COST`.

**Output** — a tuple `(purchase, payments)`:

- `purchase`: whether the group makes the purchase.
- `payments`: `{id: amount}` with **exactly one entry per offered id**.

The contract, checked automatically on every simulated round
(`validate_split_result` raises a `ValueError` naming the violation):

- every payment is non-negative;
- if `purchase` is `True`, payments must total **at least** `COST`
  (over-collection is allowed — e.g. Clarke pivot taxes — and shows up in the
  reports as budget surplus);
- if `purchase` is `False`, payments are usually all zero, but taxes are
  allowed (the Clarke mechanism charges agents who pivot the decision to
  "don't buy").

`splits/_template.py` is a copy-ready skeleton you can hand to contributors.
Four mechanisms are included: `equal_split`, `proportional_split`,
`clarke_tax_split` (equal-share VCG — provably strategyproof, the benchmark),
and `free_rider_split`.

## 2. How scoring works

A negotiator's utility in a round is:

```
u = (true_wtp if purchase else 0) − payment
```

i.e. you gain your true value for the item if it's bought, and you lose what
you pay (including any no-purchase taxes).

**The headline metric is truthfulness regret** (`truthfulness_regrets` in
`scoring.py`). For each negotiator in a sampled round, we hold everyone else's
reports fixed exactly as they were, sweep a grid of alternative reports for
this one agent, and re-run the split function for each:

```
regret = (best utility over any alternative report) − (utility of reporting true_wtp)
```

Regret is always ≥ 0. A mechanism under which honesty is always a best
response — a *strategyproof* mechanism — has regret exactly 0 for everyone,
everywhere. The bigger the regret, the more the mechanism rewards lying. This
counterfactual, per-agent measurement is the direct answer to "does honesty
pay by the negotiator's own values"; it needs no assumptions about how people
actually lie. (It's quadratic-ish in cost, so it's sampled every
`regret_every`-th round — the same rounds for every mechanism.)

Alongside regret, each report includes:

- **exploitable agent-rounds** — how *often* some misreport beats truth (vs.
  regret's *how much*);
- **forced losses** — fraction of agent-rounds where someone paid more than
  their true value (an individual-rationality violation);
- **budget surplus** — payments collected beyond the cost (burned, e.g. by
  Clarke pivot taxes);
- **average value overall and per lying strategy**, with standard errors;
- **honesty ↔ value correlation** — kept as a secondary readout, but beware:
  it's confounded (utility contains `true_wtp` directly, and value clipping
  makes high-value overstaters nearly honest), which is exactly why regret is
  the headline metric.

## 3. How the pieces connect

```
negotiator.py       Generates rounds: random groups of Negotiators, each with a
                    true_wtp and a stated_wtp produced by a lying strategy
                    (truthful / overstate / understate / random).
      |
      v
simulator.py        run_simulation() feeds the SAME sequence of seeded random
                    rounds to every split function, so results are directly
                    comparable. Each round it: calls the split function,
                    validates the output against the contract, computes
                    truthfulness regrets (on sampled rounds), and records
                    everything into that mechanism's stats.
      |
      v
split_functions.py  The contract: COST, validate_split_result(), and
                    load_split_functions(), which discovers every mechanism in
  splits/*.py       the splits/ directory by filename.
      |
      v
scoring.py          score_round() turns payments into per-agent utility;
                    truthfulness_regrets() runs the counterfactual report
                    sweep; SplitFunctionStats accumulates per-mechanism
                    metrics and formats the per-mechanism report.
      |
      v
main.py             Loads all split functions, runs the simulation, prints
                    each mechanism's detailed report, then a side-by-side
                    comparison table ranked by mean regret (lower = better
                    for honesty).
```

Reading the final table: `clarke_tax_split` sits at regret 0.00 (as theory
predicts for VCG), which doubles as a check that the harness itself is sound.
Mechanisms trade off along the other columns too — Clarke buys its perfect
honesty incentives with the most forced losses and a burned budget surplus,
while `proportional_split` has the fewest forced losses but is exploitable in
99% of agent-rounds.
