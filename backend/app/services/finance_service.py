"""Libro financiero: categorías, movimientos, costos, precios y resumen."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_contracts import CostItemView, FinancialMovementView
from app.core.clock import utc_now
from app.core.exceptions import Invalid, NotFound
from app.domain_rules import (
    calculate_suggested_price,
    movement_balance_effect,
    validate_transfer,
)
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
from app.services.authorization import assert_permission, owned_business


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
    assert_permission(db, user, "finance.write_own")
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


def list_categories(db: Session, user: User) -> list[dict[str, str]]:
    """Catálogo de categorías financieras."""
    assert_permission(db, user, "finance.read_own")
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
    assert_permission(db, user, "finance.read_own")
    if business_id:
        owned_business(db, user, business_id)
    query = _movement_query(user, business_id, date_from, date_to)
    rows = db.scalars(query.order_by(FinancialMovement.occurred_on.desc())).all()
    return [_to_view(row) for row in rows]


def create_cost(db: Session, user: User, payload) -> dict[str, str]:
    """Registra un costo del emprendimiento."""
    assert_permission(db, user, "finance.write_own")
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
    assert_permission(db, user, "finance.write_own")
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
    assert_permission(db, user, "finance.read_own")
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


def _cost_view(row: CostItem) -> CostItemView:
    return CostItemView(
        id=row.id,
        business_id=row.business_id,
        name=row.name,
        cost_type=row.cost_type,
        amount=row.amount,
        currency=row.currency,
        unit=row.unit,
        periodicity=row.periodicity,
        quantity_base=row.quantity_base,
        notes=decrypt_text(row.notes_encrypted) if row.notes_encrypted else None,
    )


def _owned_movement(db: Session, user: User, movement_id: str) -> FinancialMovement:
    """Movimiento de la usuaria; uno ajeno responde igual que uno inexistente."""
    movement = db.scalar(
        select(FinancialMovement).where(
            FinancialMovement.id == movement_id,
            FinancialMovement.user_id == user.id,
            FinancialMovement.deleted_at.is_(None),
        )
    )
    if movement is None:
        raise NotFound("Movimiento no encontrado")
    return movement


def _owned_cost(db: Session, user: User, cost_id: str) -> CostItem:
    cost = db.scalar(
        select(CostItem).where(CostItem.id == cost_id, CostItem.deleted_at.is_(None))
    )
    if cost is None:
        raise NotFound("Costo no encontrado")
    # La propiedad del costo se deriva de la del emprendimiento.
    owned_business(db, user, cost.business_id)
    return cost


def list_costs(db: Session, user: User, *, business_id: str) -> list[CostItemView]:
    """Costos vigentes del emprendimiento."""
    assert_permission(db, user, "finance.read_own")
    owned_business(db, user, business_id)
    rows = db.scalars(
        select(CostItem)
        .where(CostItem.business_id == business_id, CostItem.deleted_at.is_(None))
        .order_by(CostItem.created_at.desc())
    ).all()
    return [_cost_view(row) for row in rows]


def update_movement(db: Session, user: User, movement_id: str, payload) -> FinancialMovementView:
    """Corrige un movimiento mal registrado.

    La coherencia de la transferencia se comprueba sobre el estado resultante
    de fusionar el parche con la fila, no sobre el parche suelto, y la decide
    `domain_rules.validate_transfer`.
    """
    assert_permission(db, user, "finance.write_own")
    movement = _owned_movement(db, user, movement_id)
    changes = payload.model_dump(exclude_unset=True)

    final_type = changes.get("movement_type", movement.movement_type)
    final_scope = changes.get("scope", movement.scope)
    final_counter_scope = changes.get("counter_scope", movement.counter_scope)
    try:
        validate_transfer(final_type, final_scope, final_counter_scope)
    except ValueError as exc:
        raise Invalid(str(exc)) from exc

    if "category_id" in changes or "movement_type" in changes:
        category = db.get(FinancialCategory, changes.get("category_id", movement.category_id))
        if category is None or category.movement_type != final_type:
            raise Invalid("Categoría incompatible con el movimiento")

    if "note" in changes:
        note = changes.pop("note")
        movement.note_encrypted = encrypt_text(note) if note else None
    for field, value in changes.items():
        setattr(movement, field, value)

    write_audit(
        db,
        actor=user,
        action="finance.update",
        object_type="financial_movement",
        object_id=movement.id,
    )
    db.commit()
    return _to_view(movement)


def delete_movement(db: Session, user: User, movement_id: str) -> None:
    """Borrado lógico: el movimiento deja de contar en listados y resumen."""
    assert_permission(db, user, "finance.write_own")
    movement = _owned_movement(db, user, movement_id)
    movement.deleted_at = utc_now()
    write_audit(
        db,
        actor=user,
        action="finance.delete",
        object_type="financial_movement",
        object_id=movement.id,
    )
    db.commit()


def update_cost(db: Session, user: User, cost_id: str, payload) -> CostItemView:
    """Corrige un costo del emprendimiento."""
    assert_permission(db, user, "finance.write_own")
    cost = _owned_cost(db, user, cost_id)
    changes = payload.model_dump(exclude_unset=True)
    if "notes" in changes:
        notes = changes.pop("notes")
        cost.notes_encrypted = encrypt_text(notes) if notes else None
    for field, value in changes.items():
        setattr(cost, field, value)
    write_audit(db, actor=user, action="finance.update", object_type="cost_item", object_id=cost.id)
    db.commit()
    return _cost_view(cost)


def delete_cost(db: Session, user: User, cost_id: str) -> None:
    """Borrado lógico del costo.

    Los escenarios de precio ya calculados no se alteran:
    `pricing_scenario_costs` guarda `label_snapshot` y `amount_snapshot`, y su
    clave foránea es `ON DELETE SET NULL`.
    """
    assert_permission(db, user, "finance.write_own")
    cost = _owned_cost(db, user, cost_id)
    cost.deleted_at = utc_now()
    write_audit(db, actor=user, action="finance.delete", object_type="cost_item", object_id=cost.id)
    db.commit()
