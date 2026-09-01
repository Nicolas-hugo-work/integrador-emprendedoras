from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api_contracts import FinancialMovementCreate, SourceVersionCreate


def test_transfer_requires_different_scopes() -> None:
    with pytest.raises(ValidationError):
        FinancialMovementCreate(
            category_id="category",
            movement_type="TRANSFER",
            scope="BUSINESS",
            counter_scope="BUSINESS",
            amount=Decimal("10"),
            occurred_on=date(2026, 8, 31),
        )


def test_source_validity_dates_are_ordered() -> None:
    with pytest.raises(ValidationError):
        SourceVersionCreate(
            source_id="source",
            version_label="v1",
            valid_from=date(2026, 9, 1),
            valid_to=date(2026, 8, 1),
            content_hash="a" * 64,
            storage_key="sources/a.pdf",
        )

