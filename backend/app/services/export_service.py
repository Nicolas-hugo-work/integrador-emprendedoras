"""Exportación de los datos de la usuaria.

`POST /privacy/export` registraba una solicitud que nadie cumplía nunca: quedaba
en `PENDING` para siempre. Un worker habría necesitado dónde dejar el archivo, y
`DataExportRequest` no tiene columna de almacenamiento, así que la exportación
se **genera al vuelo** en la descarga. Sin worker, sin almacenamiento de objetos
y sin columnas nuevas.

La selección es una **lista blanca**: se enumera lo que se entrega, nunca lo que
se oculta. Así, una tabla nueva queda fuera hasta que alguien decida
explícitamente incluirla, en vez de filtrarse por olvido.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.exceptions import NotFound
from app.models.business import Business, UserPreference
from app.models.conversation import Conversation, Message, ResponseFeedback
from app.models.finance import CostItem, FinancialMovement, PricingScenario
from app.models.identity import User, UserContact
from app.models.privacy import (
    ConsentPurpose,
    DataExportRequest,
    DeletionRequest,
    UserConsent,
)
from app.security import decrypt_text
from app.services.audit_service import write_audit

#: Secciones que viajan en el archivo. Cada una corresponde a una tabla con
#: datos de la usuaria; ver `app/tasks.py::purge_due_accounts`, que borra este
#: mismo conjunto cuando se cumple el plazo de eliminación.
EXPORTED_SECTIONS = (
    "perfil",
    "preferencias",
    "contactos",
    "emprendimientos",
    "movimientos_financieros",
    "costos",
    "escenarios_de_precio",
    "conversaciones",
    "consentimientos",
    "retroalimentacion",
    "solicitudes_de_eliminacion",
)

#: Tablas con datos de la usuaria que se excluyen a propósito. Entregar
#: credenciales o tokens en un archivo descargable sería crear el problema que
#: la exportación intenta resolver.
EXCLUDED_TABLES = {
    # Credenciales: entregarlas en un archivo descargable seria crear el
    # problema que la exportacion intenta resolver.
    "password_credentials": "hash de contraseña",
    "sessions": "tokens de sesión activos",
    "auth_challenges": "códigos de verificación en curso",
    # Vacias mientras no exista la funcionalidad que las escribe.
    "audio_artifacts": "no existe carga de audio todavía",
    "generated_contents": "no existe generación de contenido todavía",
    "escalation_events": "no existe derivación a personas todavía",
    "organization_memberships": "no existe gestión de organizaciones todavía",
    # Derivables o meramente operativas.
    "business_memberships": "se deduce de los emprendimientos exportados",
    "user_roles": "rol operativo dentro del sistema, no dato personal",
    "data_export_requests": "metadatos de esta misma exportación",
}


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _decrypt(value: str | None) -> str | None:
    return decrypt_text(value) if value else None


def build_export(db: Session, user: User) -> dict[str, Any]:
    """Arma el contenido exportable de una usuaria."""
    business_ids = list(
        db.scalars(select(Business.id).where(Business.owner_user_id == user.id))
    )

    contactos = db.scalars(
        select(UserContact).where(UserContact.user_id == user.id)
    ).all()
    negocios = db.scalars(
        select(Business).where(Business.owner_user_id == user.id)
    ).all()
    movimientos = db.scalars(
        select(FinancialMovement).where(FinancialMovement.user_id == user.id)
    ).all()
    costos = (
        db.scalars(select(CostItem).where(CostItem.business_id.in_(business_ids))).all()
        if business_ids
        else []
    )
    escenarios = db.scalars(
        select(PricingScenario).where(PricingScenario.created_by_user_id == user.id)
    ).all()
    conversaciones = db.scalars(
        select(Conversation).where(Conversation.user_id == user.id)
    ).all()
    consentimientos = db.execute(
        select(UserConsent, ConsentPurpose.code)
        .join(ConsentPurpose, ConsentPurpose.id == UserConsent.purpose_id)
        .where(UserConsent.user_id == user.id)
        .order_by(UserConsent.decided_at)
    ).all()
    opiniones = db.scalars(
        select(ResponseFeedback).where(ResponseFeedback.user_id == user.id)
    ).all()
    preferencias = db.get(UserPreference, user.id)
    eliminaciones = db.scalars(
        select(DeletionRequest).where(DeletionRequest.user_id == user.id)
    ).all()

    mensajes_por_conversacion: dict[str, list[dict[str, Any]]] = {}
    if conversaciones:
        mensajes = db.scalars(
            select(Message)
            .where(Message.conversation_id.in_([c.id for c in conversaciones]))
            .order_by(Message.conversation_id, Message.sequence_number)
        ).all()
        for mensaje in mensajes:
            mensajes_por_conversacion.setdefault(mensaje.conversation_id, []).append(
                {
                    "numero": mensaje.sequence_number,
                    "emisor": mensaje.sender,
                    "contenido": _decrypt(mensaje.content_encrypted),
                    "creado_en": _plain(mensaje.created_at),
                }
            )

    return {
        "generado_en": _plain(utc_now()),
        "formato": "JSON",
        "excluido_a_proposito": sorted(EXCLUDED_TABLES.values()),
        "perfil": {
            "id": user.id,
            "estado": user.status,
            "idioma": user.locale,
            "zona_horaria": user.timezone,
            "creado_en": _plain(user.created_at),
        },
        "preferencias": (
            {
                "alto_contraste": preferencias.high_contrast,
                "movimiento_reducido": preferencias.reduced_motion,
                "voz_habilitada": preferencias.voice_enabled,
                "velocidad_de_lectura": preferencias.tts_speed,
                "largo_de_respuesta": preferencias.response_length,
            }
            if preferencias
            else None
        ),
        "contactos": [
            {
                "tipo": fila.contact_type,
                "valor": fila.value_normalized,
                "verificado_en": _plain(fila.verified_at),
                "principal": fila.is_primary,
            }
            for fila in contactos
        ],
        "emprendimientos": [
            {
                "id": fila.id,
                "nombre": fila.name,
                "etapa": fila.stage,
                "actividad": fila.activity,
                "departamento": fila.department_code,
                "municipio": fila.municipality,
                "estado": fila.status,
                "eliminado_en": _plain(fila.deleted_at),
            }
            for fila in negocios
        ],
        "movimientos_financieros": [
            {
                "id": fila.id,
                "emprendimiento_id": fila.business_id,
                "tipo": fila.movement_type,
                "ambito": fila.scope,
                "monto": _plain(fila.amount),
                "moneda": fila.currency,
                "fecha": _plain(fila.occurred_on),
                "nota": _decrypt(fila.note_encrypted),
                "eliminado_en": _plain(fila.deleted_at),
            }
            for fila in movimientos
        ],
        "costos": [
            {
                "id": fila.id,
                "emprendimiento_id": fila.business_id,
                "nombre": fila.name,
                "tipo": fila.cost_type,
                "monto": _plain(fila.amount),
                "moneda": fila.currency,
                "unidad": fila.unit,
                "notas": _decrypt(fila.notes_encrypted),
                "eliminado_en": _plain(fila.deleted_at),
            }
            for fila in costos
        ],
        "escenarios_de_precio": [
            {
                "id": fila.id,
                "emprendimiento_id": fila.business_id,
                "producto": fila.product_name,
                "unidades": _plain(fila.units),
                "margen_porcentual": _plain(fila.margin_percent),
                "costo_unitario": _plain(fila.unit_cost),
                "precio_sugerido": _plain(fila.suggested_price),
                "moneda": fila.currency,
            }
            for fila in escenarios
        ],
        "conversaciones": [
            {
                "id": fila.id,
                "emprendimiento_id": fila.business_id,
                "titulo": _decrypt(fila.title_encrypted),
                "tema": fila.topic_code,
                "estado": fila.status,
                "mensajes": mensajes_por_conversacion.get(fila.id, []),
            }
            for fila in conversaciones
        ],
        "consentimientos": [
            {
                "finalidad": codigo,
                "decision": consentimiento.decision,
                "decidido_en": _plain(consentimiento.decided_at),
                "origen": consentimiento.source,
            }
            for consentimiento, codigo in consentimientos
        ],
        "solicitudes_de_eliminacion": [
            {
                "solicitada_en": _plain(fila.requested_at),
                "purga_prevista": _plain(fila.purge_due_at),
                "estado": fila.status,
                "alcance": fila.scope,
            }
            for fila in eliminaciones
        ],
        "retroalimentacion": [
            {
                "mensaje_id": fila.message_id,
                "tipo": fila.feedback_type,
                "comentario": _decrypt(fila.comment_encrypted),
                "estado": fila.status,
            }
            for fila in opiniones
        ],
    }


def download_export(db: Session, user: User, request_id: str) -> dict[str, Any]:
    """Entrega la exportación y marca la solicitud como cumplida.

    Una solicitud ajena responde igual que una inexistente.
    """
    solicitud = db.scalar(
        select(DataExportRequest).where(
            DataExportRequest.id == request_id,
            DataExportRequest.user_id == user.id,
        )
    )
    if solicitud is None:
        raise NotFound("Solicitud de exportación no encontrada")

    contenido = build_export(db, user)
    solicitud.status = "READY"
    solicitud.completed_at = utc_now()
    write_audit(
        db,
        actor=user,
        action="account.export_download",
        object_type="data_export_request",
        object_id=solicitud.id,
    )
    db.commit()
    return {"solicitud_id": solicitud.id, **contenido}
