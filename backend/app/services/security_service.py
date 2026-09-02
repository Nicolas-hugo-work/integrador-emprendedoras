"""Alertas de seguridad.

El límite de intentos que introdujo `v0.2.0` bloquea una cuenta en memoria del
proceso y no deja nada sobre lo que actuar. `security_alerts` existe desde el
esquema inicial y nunca se escribió: es la cola de trabajo de la
administradora, y la vía —prevista por el esquema— para llegar desde un hecho
sospechoso hasta una cuenta concreta.

A diferencia de `AuditEventView`, aquí **sí** viaja el `user_id`. Es el único
punto donde se levanta la seudonimización, y es deliberado: sin él la
administradora no podría suspender a nadie. La lectura de la cola queda
auditada.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_contracts import SecurityAlertView
from app.core.clock import utc_now
from app.core.exceptions import Conflict, NotFound
from app.models.admin_research import SecurityAlert
from app.models.identity import User
from app.services.audit_service import write_audit
from app.services.authorization import assert_permission

#: Tope de página, coherente con el visor de auditoría.
MAX_PAGE = 200

#: Tipos que levanta el limitador de intentos, con su severidad.
LOCKOUT_ALERTS = {
    "login.contact_locked": ("MEDIUM", "Bloqueo de una cuenta por intentos fallidos"),
    "login.address_locked": ("HIGH", "Bloqueo de una dirección por intentos fallidos"),
    "verification.address_locked": (
        "MEDIUM",
        "Bloqueo de una dirección al canjear códigos de verificación",
    ),
}


def raise_lockout_alert(
    db: Session, *, alert_type: str, attempts: int, user: User | None = None
) -> SecurityAlert | None:
    """Levanta una alerta por bloqueo, sin duplicar las que siguen abiertas.

    La descripción **nunca** incluye el contacto probado ni la contraseña: solo
    el tipo de bloqueo y cuántos intentos lo provocaron. Añadir el contacto
    convertiría la cola en un registro de quién intentó entrar dónde.

    Si ya hay una alerta `OPEN` del mismo tipo para la misma cuenta no se crea
    otra: mientras nadie la atienda, repetir el bloqueo no aporta información
    nueva y solo ensuciaría la cola. El bloqueo sigue aplicándose igual.
    """
    severity, resumen = LOCKOUT_ALERTS[alert_type]
    user_id = user.id if user else None

    misma_cuenta = (
        SecurityAlert.user_id.is_(None)
        if user_id is None
        else SecurityAlert.user_id == user_id
    )
    abierta = db.scalar(
        select(SecurityAlert).where(
            SecurityAlert.alert_type == alert_type,
            SecurityAlert.status == "OPEN",
            misma_cuenta,
        )
    )
    if abierta is not None:
        return None

    alerta = SecurityAlert(
        alert_type=alert_type,
        severity=severity,
        status="OPEN",
        user_id=user_id,
        description=f"{resumen}: {attempts} intentos fallidos consecutivos.",
    )
    db.add(alerta)
    return alerta


def list_alerts(
    db: Session,
    user: User,
    *,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SecurityAlertView]:
    """Cola de alertas. Leerla es de auditoría; actuar sobre ella, de administración."""
    assert_permission(db, user, "audit.read")

    query = select(SecurityAlert)
    if status:
        query = query.where(SecurityAlert.status == status)
    if severity:
        query = query.where(SecurityAlert.severity == severity)

    rows = db.scalars(
        query.order_by(SecurityAlert.created_at.desc())
        .limit(min(max(limit, 1), MAX_PAGE))
        .offset(max(offset, 0))
    ).all()
    write_audit(
        db, actor=user, action="security_alert.read", object_type="security_alert", object_id=None
    )
    db.commit()
    return [SecurityAlertView.model_validate(row) for row in rows]


def _set_status(db: Session, user: User, alert_id: str, nuevo: str) -> dict[str, str]:
    assert_permission(db, user, "account.suspend")
    alerta = db.get(SecurityAlert, alert_id)
    if alerta is None:
        raise NotFound("Alerta no encontrada")
    if alerta.status == nuevo:
        raise Conflict(f"La alerta ya está en estado {nuevo}")

    alerta.status = nuevo
    alerta.resolved_at = utc_now() if nuevo == "RESOLVED" else None
    write_audit(
        db,
        actor=user,
        action=f"security_alert.{nuevo.casefold()}",
        object_type="security_alert",
        object_id=alerta.id,
    )
    db.commit()
    return {"id": alerta.id, "status": alerta.status}


def acknowledge_alert(db: Session, user: User, alert_id: str) -> dict[str, str]:
    """Marca la alerta como tomada, sin darla por cerrada."""
    return _set_status(db, user, alert_id, "ACKNOWLEDGED")


def resolve_alert(db: Session, user: User, alert_id: str) -> dict[str, str]:
    """Cierra la alerta y vuelve a habilitar el aviso para ese tipo y cuenta."""
    return _set_status(db, user, alert_id, "RESOLVED")
