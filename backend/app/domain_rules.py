from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")


def validate_transfer(movement_type: str, scope: str, counter_scope: str | None) -> None:
    if movement_type == "TRANSFER":
        if counter_scope is None or counter_scope == scope:
            raise ValueError("La transferencia requiere origen y destino diferentes")
    elif counter_scope is not None:
        raise ValueError("counter_scope solo corresponde a transferencias")


def movement_balance_effect(movement_type: str, amount: Decimal) -> Decimal:
    if amount <= 0:
        raise ValueError("El monto debe ser positivo")
    if movement_type == "INCOME":
        return amount
    if movement_type in {"EXPENSE", "COST"}:
        return -amount
    if movement_type == "TRANSFER":
        return Decimal("0")
    raise ValueError("Tipo de movimiento desconocido")


def calculate_suggested_price(
    costs: list[Decimal], units: Decimal, margin_percent: Decimal
) -> tuple[Decimal, Decimal]:
    if units <= 0:
        raise ValueError("Las unidades deben ser positivas")
    if margin_percent < 0 or margin_percent > 1000:
        raise ValueError("Margen fuera del rango permitido")
    if any(cost < 0 for cost in costs):
        raise ValueError("Los costos no pueden ser negativos")
    unit_cost = (sum(costs, Decimal("0")) / units).quantize(MONEY, ROUND_HALF_UP)
    suggested = (unit_cost * (Decimal("1") + margin_percent / Decimal("100"))).quantize(
        MONEY, ROUND_HALF_UP
    )
    return unit_cost, suggested


def validate_normative_response(
    *, is_normative: bool, abstained: bool, citation_count: int, warning: str | None
) -> None:
    if not is_normative:
        return
    if abstained:
        return
    if citation_count < 1 or not warning:
        raise ValueError("Una respuesta normativa requiere cita vigente y advertencia")


def audio_purge_deadline(uploaded_at: datetime, confirmed_at: datetime | None) -> datetime:
    hard_limit = uploaded_at + timedelta(hours=24)
    return min(hard_limit, confirmed_at) if confirmed_at else hard_limit


def account_purge_deadline(requested_at: datetime) -> datetime:
    return requested_at + timedelta(days=30)


def optional_feature_allowed(latest_decision: str | None) -> bool:
    return latest_decision == "GRANTED"

