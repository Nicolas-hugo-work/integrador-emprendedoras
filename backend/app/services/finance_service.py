"""Libro financiero: categorías, movimientos, costos, precios y resumen."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_contracts import FinancialMovementView
from app.core.exceptions import Invalid
from app.domain_rules import calculate_suggested_price, movement_balance_effect
from app.models.finance import (
    CostItem,
    FinancialCategory,
    FinancialMovement,
    PricingScenario,
    PricingScenarioCost,
)
from app.models.identity import User
from app.security import decrypt_text, encrypt_text
from app.services.audit_service import write_audit
from app.services.authorization import owned_business


def _to_view(row: FinancialMovement) -> FinancialMovementView:
    return FinancialMovementView(
        id=row.id,
        business_id=row.business_id,
        category_id=row.category_id,
        movement_type=row.movement_type,
        scope=row.scope,
        counter_scope=row.counter_scope,
        amount=row.amount,
        currency=row.currency,
        occurred_on=row.occurred_on,
        note=decrypt_text(row.note_encrypted) if row.note_encrypted else None,
    )


def create_movement(db: Session, user: User, payload) -> FinancialMovementView:
    """Registra un movimiento del libro financiero.

    La coherencia de una transferencia ya la valida `FinancialMovementCreate`,
    que delega en `domain_rules.validate_transfer`.
    """
    if payload.business_id:
        owned_business(db, user, payload.business_id)
    elif payload.scope == "BUSINESS":
        raise Invalid("Un movimiento del negocio requiere business_id")
    category = db.get(FinancialCategory, payload.category_id)
    if category is None or category.movement_type != payload.movement_type:
        raise Invalid("Categoría incompatible con el movimiento")
    movement = FinancialMovement(
        user_id=user.id,
        business_id=payload.business_id,
        category_id=payload.category_id,
        movement_type=payload.movement_type,
        scope=payload.scope,
        counter_scope=payload.counter_scope,
        amount=payload.amount,
        currency=payload.currency,
        occurred_on=payload.occurred_on,
        note_encrypted=encrypt_text(payload.note) if payload.note else None,
    )
    db.add(movement)
    db.flush()
    write_audit(
        db,
        actor=user,
        action="finance.create",
        object_type="financial_movement",
        object_id=movement.id,
    )
    db.commit()
    return _to_view(movement)


def list_categories(db: Session) -> list[dict[str, str]]:
    """Catálogo de categorías financieras."""
    rows = db.scalars(
        select(FinancialCategory).order_by(FinancialCategory.movement_type, FinancialCategory.name)
    ).all()
    return [
        {"id": row.id, "code": row.code, "name": row.name, "movement_type": row.movement_type}
        for row in rows
    ]


def _movement_query(
    user: User,
    business_id: str | None,
    date_from: date | None,
    date_to: date | None,
):
    query = select(FinancialMovement).where(
        FinancialMovement.user_id == user.id, FinancialMovement.deleted_at.is_(None)
    )
    if business_id:
        query = query.where(FinancialMovement.business_id == business_id)
    if date_from:
        query = query.where(FinancialMovement.occurred_on >= date_from)
    if date_to:
        query = query.where(FinancialMovement.occurred_on <= date_to)
    return query


def list_movements(
    db: Session,
    user: User,
    *,
    business_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[FinancialMovementView]:
    """Lista los movimientos de la usuaria, opcionalmente acotados."""
    if business_id:
        owned_business(db, user, business_id)
    query = _movement_query(user, business_id, date_from, date_to)
    rows = db.scalars(query.order_by(FinancialMovement.occurred_on.desc())).all()
    return [_to_view(row) for row in rows]


def create_cost(db: Session, user: User, payload) -> dict[str, str]:
    """Registra un costo del emprendimiento."""
    owned_business(db, user, payload.business_id)
    cost = CostItem(
        business_id=payload.business_id,
        name=payload.name,
        cost_type=payload.cost_type,
        amount=payload.amount,
        currency=payload.currency,
        unit=payload.unit,
        periodicity=payload.periodicity,
        quantity_base=payload.quantity_base,
        notes_encrypted=encrypt_text(payload.notes) if payload.notes else None,
    )
    db.add(cost)
    db.commit()
    return {"id": cost.id}


def create_pricing_scenario(db: Session, user: User, payload) -> dict[str, str]:
    """Calcula un escenario de precio y congela la fotografía de costos."""
    owned_business(db, user, payload.business_id)
    costs = list(
        db.scalars(
            select(CostItem).where(
                CostItem.business_id == payload.business_id,
                CostItem.id.in_(payload.cost_item_ids),
                CostItem.deleted_at.is_(None),
            )
        )
    )
    if len(costs) != len(set(payload.cost_item_ids)):
        raise Invalid("Uno o más costos no existen")
    unit_cost, suggested = calculate_suggested_price(
        [item.amount for item in costs], payload.units, payload.margin_percent
    )
    scenario = PricingScenario(
        business_id=payload.business_id,
        created_by_user_id=user.id,
        product_name=payload.product_name,
        units=payload.units,
        margin_percent=payload.margin_percent,
        unit_cost=unit_cost,
        suggested_price=suggested,
        currency=payload.currency,
        formula_version="simple-v1",
        assumptions={"cost_count": len(costs)},
    )
    db.add(scenario)
    db.flush()
    for item in costs:
        db.add(
            PricingScenarioCost(
                scenario_id=scenario.id,
                cost_item_id=item.id,
                label_snapshot=item.name,
                amount_snapshot=item.amount,
                allocation_quantity=item.quantity_base,
            )
        )
    db.commit()
    return {"id": scenario.id, "unit_cost": str(unit_cost), "suggested_price": str(suggested)}


def financial_summary(
    db: Session,
    user: User,
    *,
    business_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, str]:
    """Ingresos, salidas y saldo del emprendimiento en el periodo.

    El efecto de cada movimiento sobre el saldo lo decide
    `domain_rules.movement_balance_effect`, en lugar del `if/elif` que `v0.1.0`
    repetía aquí. Las transferencias siguen sin alterar el saldo.
    """
    owned_business(db, user, business_id)
    query = _movement_query(user, business_id, date_from, date_to)
    income, outflow = Decimal("0"), Decimal("0")
    for movement in db.scalars(query):
        effect = movement_balance_effect(movement.movement_type, movement.amount)
        if effect > 0:
            income += effect
        elif effect < 0:
            outflow += -effect
    return {"income": str(income), "outflow": str(outflow), "balance": str(income - outflow)}
