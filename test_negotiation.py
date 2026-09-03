"""Unit tests: split-function contracts, hand-computed rounds, and the
strategyproofness of the Clarke mechanism under the regret metric.

Run with:  python -m unittest test_negotiation
"""
import random
import unittest

from negotiator import Negotiator, generate_negotiators
from scoring import score_round, truthfulness_regrets
from split_functions import COST, load_split_functions, validate_split_result

SPLIT_FUNCTIONS = load_split_functions()
equal_split = SPLIT_FUNCTIONS["equal_split"]
proportional_split = SPLIT_FUNCTIONS["proportional_split"]
clarke_tax_split = SPLIT_FUNCTIONS["clarke_tax_split"]
free_rider_split = SPLIT_FUNCTIONS["free_rider_split"]


class TestEqualSplit(unittest.TestCase):
    def test_purchase_and_even_shares(self):
        purchase, payments = equal_split([(0, 300), (1, 300)])
        self.assertTrue(purchase)
        self.assertEqual(payments, {0: 250.0, 1: 250.0})

    def test_no_purchase_when_short(self):
        purchase, payments = equal_split([(0, 100), (1, 100)])
        self.assertFalse(purchase)
        self.assertEqual(payments, {0: 0.0, 1: 0.0})


class TestProportionalSplit(unittest.TestCase):
    def test_shares_proportional_to_stated(self):
        purchase, payments = proportional_split([(0, 300), (1, 200)])
        self.assertTrue(purchase)
        self.assertAlmostEqual(payments[0], 300.0)
        self.assertAlmostEqual(payments[1], 200.0)


class TestClarkeTaxSplit(unittest.TestCase):
    def test_non_pivotal_agents_pay_only_their_share(self):
        # Shares 250 each; nets 350, 350 -- neither is pivotal.
        purchase, payments = clarke_tax_split([(0, 600), (1, 600)])
        self.assertTrue(purchase)
        self.assertEqual(payments, {0: 250.0, 1: 250.0})

    def test_pivotal_buyer_pays_pivot_tax(self):
        # Shares 250; nets 150 and -100; total net 50 -> buy.
        # Agent 0 is pivotal (others' net = -100): pays 250 + 100.
        # Agent 1 is not (others' net = 150): pays 250.
        purchase, payments = clarke_tax_split([(0, 400), (1, 150)])
        self.assertTrue(purchase)
        self.assertAlmostEqual(payments[0], 350.0)
        self.assertAlmostEqual(payments[1], 250.0)

    def test_blocking_agent_taxed_even_without_purchase(self):
        # Shares 250; nets 200 and -240; total net -40 -> no purchase.
        # Agent 1 pivoted the decision to "don't buy" and destroyed the
        # others' surplus of 200, so pays a 200 tax despite no purchase.
        purchase, payments = clarke_tax_split([(0, 450), (1, 10)])
        self.assertFalse(purchase)
        self.assertAlmostEqual(payments[0], 0.0)
        self.assertAlmostEqual(payments[1], 200.0)

    def test_strategyproof_zero_regret_on_random_rounds(self):
        rng = random.Random(7)
        for _ in range(200):
            negotiators = generate_negotiators(rng)
            regrets = truthfulness_regrets(
                negotiators, clarke_tax_split, grid_step=25
            )
            for agent_id, regret in regrets.items():
                self.assertAlmostEqual(
                    regret, 0.0, places=6,
                    msg=f"agent {agent_id} could profit by misreporting",
                )


class TestFreeRiderSplit(unittest.TestCase):
    def test_low_reporter_free_rides(self):
        # Initial share 500/3; agent 2 (50) is excused; agents 0 and 1
        # split the cost at 250 each, which both can afford.
        purchase, payments = free_rider_split([(0, 400), (1, 300), (2, 50)])
        self.assertTrue(purchase)
        self.assertAlmostEqual(payments[0], 250.0)
        self.assertAlmostEqual(payments[1], 250.0)
        self.assertEqual(payments[2], 0.0)

    def test_differs_from_equal_split(self):
        offers = [(0, 400), (1, 300), (2, 50)]
        self.assertNotEqual(free_rider_split(offers), equal_split(offers))

    def test_fallback_when_exclusions_would_empty_payer_set(self):
        # Total 500 -> buy. Agent 1 excused (1 < 250); then agent 0's share
        # is 500 > 499, but the last non-empty payer set is charged anyway.
        purchase, payments = free_rider_split([(0, 499), (1, 1)])
        self.assertTrue(purchase)
        self.assertAlmostEqual(payments[0], 500.0)
        self.assertEqual(payments[1], 0.0)

    def test_no_purchase_when_short(self):
        purchase, payments = free_rider_split([(0, 100), (1, 100)])
        self.assertFalse(purchase)
        self.assertEqual(payments, {0: 0.0, 1: 0.0})


class TestValidateSplitResult(unittest.TestCase):
    OFFERS = [(0, 300), (1, 300)]

    def test_accepts_valid_result(self):
        validate_split_result(self.OFFERS, True, {0: 250.0, 1: 250.0})
        validate_split_result(self.OFFERS, False, {0: 0.0, 1: 0.0})

    def test_rejects_mismatched_ids(self):
        with self.assertRaises(ValueError):
            validate_split_result(self.OFFERS, True, {0: 500.0})

    def test_rejects_negative_payment(self):
        with self.assertRaises(ValueError):
            validate_split_result(self.OFFERS, True, {0: 550.0, 1: -50.0})

    def test_rejects_undercollection_on_purchase(self):
        with self.assertRaises(ValueError):
            validate_split_result(self.OFFERS, True, {0: 100.0, 1: 100.0})

    def test_all_discovered_functions_satisfy_contract(self):
        rng = random.Random(11)
        for _ in range(500):
            negotiators = generate_negotiators(rng)
            offers = [(n.id, n.stated_wtp) for n in negotiators]
            for name, fn in SPLIT_FUNCTIONS.items():
                purchase, payments = fn(offers)
                try:
                    validate_split_result(offers, purchase, payments)
                except ValueError as e:
                    self.fail(f"{name} violated the contract: {e}")


class TestScoring(unittest.TestCase):
    def test_score_round_subtracts_payment_from_true_value(self):
        negotiators = [
            Negotiator(id=0, true_wtp=400, stated_wtp=400, strategy="truthful"),
            Negotiator(id=1, true_wtp=100, stated_wtp=150, strategy="overstate"),
        ]
        values = score_round(negotiators, True, {0: 350.0, 1: 250.0})
        self.assertAlmostEqual(values[0], 50.0)
        self.assertAlmostEqual(values[1], -150.0)

    def test_score_round_charges_taxes_even_without_purchase(self):
        negotiators = [
            Negotiator(id=0, true_wtp=450, stated_wtp=450, strategy="truthful"),
            Negotiator(id=1, true_wtp=10, stated_wtp=10, strategy="truthful"),
        ]
        values = score_round(negotiators, False, {0: 0.0, 1: 200.0})
        self.assertAlmostEqual(values[0], 0.0)
        self.assertAlmostEqual(values[1], -200.0)

    def test_regret_positive_when_misreporting_helps(self):
        # Under proportional_split, understating shifts cost onto the other
        # agent, so a truthful high-value agent has positive regret.
        negotiators = [
            Negotiator(id=0, true_wtp=600, stated_wtp=600, strategy="truthful"),
            Negotiator(id=1, true_wtp=600, stated_wtp=600, strategy="truthful"),
        ]
        regrets = truthfulness_regrets(negotiators, proportional_split, grid_step=25)
        self.assertGreater(regrets[0], 0.0)


if __name__ == "__main__":
    unittest.main()
