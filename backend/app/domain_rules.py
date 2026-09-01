from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")


def validate_transfer(movement_type: str, scope: str, counter_scope: str | None) -> None:
    """Única definición de la coherencia de una transferencia.

    `FinancialMovementCreate` delega aquí, de modo que la regla se aplica en el
    borde HTTP —Pydantic convierte el `ValueError` en un 422— sin quedar
    duplicada. Los textos son los que la API ya devolvía en v0.1.0.
    """
    if movement_type == "TRANSFER":
        if counter_scope is None or counter_scope == scope:
            raise ValueError("Una transferencia requiere ámbitos de origen y destino diferentes")
    elif counter_scope is not None:
        raise ValueError("counter_scope solo se admite para transferencias")


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
    """Plazo de purga de un audio: al confirmar la transcripción o a las 24 horas.

    Todavía no la invoca ningún caso de uso porque no existe un endpoint de
    carga de audio: `tasks.purge_audio_metadata` lee `AudioArtifact.purge_at`,
    pero nada crea esas filas. Queda como contrato listo para v0.3.0, cuando se
    añada la carga de notas de voz; su comportamiento está fijado por pruebas.
    """
    hard_limit = uploaded_at + timedelta(hours=24)
    return min(hard_limit, confirmed_at) if confirmed_at else hard_limit


def account_purge_deadline(requested_at: datetime) -> datetime:
    return requested_at + timedelta(days=30)


def optional_feature_allowed(latest_decision: str | None) -> bool:
    """Indica si una finalidad opcional está vigente para la usuaria.

    Tampoco tiene todavía punto de uso: la API no expone una lectura de
    consentimientos (`GET /consents`), así que la pantalla de privacidad
    mantiene el estado en el cliente. Añadir ese endpoint cambiaría la
    superficie HTTP más allá de lo aprobado para v0.2.0, de modo que la regla
    queda documentada y probada a la espera de v0.3.0.
    """
    return latest_decision == "GRANTED"

