from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FinancialCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_categories"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('INCOME','EXPENSE','COST','TRANSFER')", name="valid_type"
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    is_system: Mapped[bool] = mapped_column(default=True, nullable=False)


class FinancialMovement(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "financial_movements"
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint(
            "movement_type IN ('INCOME','EXPENSE','COST','TRANSFER')", name="valid_type"
        ),
        CheckConstraint("scope IN ('BUSINESS','HOUSEHOLD')", name="valid_scope"),
        CheckConstraint(
            "counter_scope IS NULL OR counter_scope IN ('BUSINESS','HOUSEHOLD')",
            name="valid_counter_scope",
        ),
        CheckConstraint(
            "(movement_type = 'TRANSFER' AND counter_scope IS NOT NULL AND counter_scope <> scope) "
            "OR (movement_type <> 'TRANSFER' AND counter_scope IS NULL)",
            name="valid_transfer",
        ),
        Index(
            "ix_financial_movements_business_date",
            "business_id",
            "occurred_on",
            "movement_type",
            "deleted_at",
        ),
        Index("ix_financial_movements_user_date", "user_id", "occurred_on"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    business_id: Mapped[str | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("financial_categories.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    counter_scope: Mapped[str | None] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BOB", nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    note_encrypted: Mapped[str | None] = mapped_column(Text)


class CostItem(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "cost_items"
    __table_args__ = (
        CheckConstraint("cost_type IN ('FIXED','VARIABLE')", name="valid_type"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("quantity_base > 0", name="positive_quantity"),
        Index("ix_cost_items_business_active", "business_id", "is_active", "deleted_at"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    cost_type: Mapped[str] = mapped_column(String(12), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BOB", nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    periodicity: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_base: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=1, nullable=False)
    notes_encrypted: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class PricingScenario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pricing_scenarios"
    __table_args__ = (
        CheckConstraint("units > 0", name="positive_units"),
        CheckConstraint("margin_percent >= 0 AND margin_percent <= 1000", name="valid_margin"),
        CheckConstraint("unit_cost >= 0 AND suggested_price >= 0", name="nonnegative_prices"),
        Index("ix_pricing_scenarios_business_created", "business_id", "created_at"),
    )

    business_id: Mapped[str] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    units: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    margin_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    suggested_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BOB", nullable=False)
    formula_version: Mapped[str] = mapped_column(String(24), nullable=False)
    assumptions: Mapped[dict] = mapped_column(JSON, nullable=False)


class PricingScenarioCost(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pricing_scenario_costs"
    __table_args__ = (
        CheckConstraint("amount_snapshot >= 0", name="nonnegative_amount"),
        CheckConstraint("allocation_quantity > 0", name="positive_allocation"),
    )

    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("pricing_scenarios.id", ondelete="CASCADE"), nullable=False
    )
    cost_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("cost_items.id", ondelete="SET NULL")
    )
    label_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    allocation_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

