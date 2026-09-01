import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain_rules import (
    account_purge_deadline,
    audio_purge_deadline,
    calculate_suggested_price,
    movement_balance_effect,
    optional_feature_allowed,
    validate_normative_response,
    validate_transfer,
)


class DomainRulesTest(unittest.TestCase):
    def test_transfer_does_not_change_income_balance(self) -> None:
        validate_transfer("TRANSFER", "HOUSEHOLD", "BUSINESS")
        self.assertEqual(movement_balance_effect("TRANSFER", Decimal("100")), Decimal("0"))

    def test_invalid_transfer_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_transfer("TRANSFER", "BUSINESS", "BUSINESS")

    def test_pricing_is_reproducible(self) -> None:
        unit_cost, suggested = calculate_suggested_price(
            [Decimal("80"), Decimal("20")], Decimal("10"), Decimal("25")
        )
        self.assertEqual(unit_cost, Decimal("10.00"))
        self.assertEqual(suggested, Decimal("12.50"))

    def test_normative_answer_needs_citation_and_warning(self) -> None:
        with self.assertRaises(ValueError):
            validate_normative_response(
                is_normative=True,
                abstained=False,
                citation_count=0,
                warning="Información educativa",
            )
        validate_normative_response(
            is_normative=True,
            abstained=True,
            citation_count=0,
            warning=None,
        )

    def test_privacy_deadlines(self) -> None:
        uploaded = datetime(2026, 8, 31, 12, 0)
        confirmed = uploaded + timedelta(hours=2)
        self.assertEqual(audio_purge_deadline(uploaded, confirmed), confirmed)
        self.assertEqual(account_purge_deadline(uploaded), uploaded + timedelta(days=30))
        self.assertFalse(optional_feature_allowed("WITHDRAWN"))


if __name__ == "__main__":
    unittest.main()

