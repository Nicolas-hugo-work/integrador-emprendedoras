"""Conversaciones, consulta al asistente RAG y retroalimentación.

Desde `v0.7.0` la recuperación usa el índice `FULLTEXT` que existía sin usarse
desde `0001`, en lugar de las coincidencias `LIKE` de `v0.1.0`. El cambio se
mide con el banco de evaluación (`evaluation_service`), que es lo que permite
afirmar que mejoró en vez de suponerlo.

El esquema vectorial (`source_chunk_embeddings`, `VECTOR(768)`,
`idx_chunk_embedding`) sigue dormido a propósito: es la mejora siguiente, y
ahora será medible.
"""

import hashlib
import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import match
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api_contracts import AssistantQueryResponse, Citation, ConversationView
from app.core.exceptions import Conflict, NotFound
from app.domain_rules import validate_normative_response
from app.models.conversation import AIRun, Conversation, Message, MessageCitation, ResponseFeedback
from app.models.identity import User
from app.models.rag import Source, SourceChunk, SourcePublisher, SourceVersion
from app.security import decrypt_text, encrypt_text
from app.services.authorization import assert_permission, owned_business

#: Identidad de la implementación que produce las respuestas. El banco de
#: evaluación etiqueta sus corridas con estos mismos valores, para que una
#: corrida quede atribuida a la recuperación que la produjo.
MODEL_NAME = "retrieval-only-mvp"
MODEL_VERSION = "v2"

NORMATIVE_TERMS = {
    "nit", "impuesto", "tributario", "tributaria", "seprec", "formalización",
    "formalizacion", "registro", "ley", "normativa", "trámite", "tramite",
}

ABSTENTION_ANSWER = (
    "No encontré evidencia suficiente en las fuentes publicadas para responder con seguridad. "
    "Puedes reformular la consulta o revisar los enlaces oficiales disponibles."
)
ABSTENTION_WARNING = "El sistema se abstuvo para evitar información inventada o desactualizada."
NORMATIVE_WARNING = (
    "Información educativa sujeta a cambios. Verifique la vigencia en la fuente "
    "oficial o consulte a una persona profesional competente."
)


def _to_view(row: Conversation) -> ConversationView:
    return ConversationView(
        id=row.id,
        business_id=row.business_id,
        title=decrypt_text(row.title_encrypted) if row.title_encrypted else None,
        topic_code=row.topic_code,
        status=row.status,
        updated_at=row.updated_at,
    )


def create_conversation(db: Session, user: User, payload) -> ConversationView:
    """Abre una conversación, opcionalmente ligada a un emprendimiento."""
    assert_permission(db, user, "conversation.manage_own")
    if payload.business_id:
        owned_business(db, user, payload.business_id)
    conversation = Conversation(
        user_id=user.id,
        business_id=payload.business_id,
        title_encrypted=encrypt_text(payload.title) if payload.title else None,
        topic_code=payload.topic_code,
    )
    db.add(conversation)
    db.commit()
    return _to_view(conversation)


def list_conversations(db: Session, user: User) -> list[ConversationView]:
    """Lista las conversaciones vigentes de la usuaria."""
    assert_permission(db, user, "conversation.manage_own")
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [_to_view(row) for row in rows]


@dataclass(frozen=True)
class Answered:
    """Lo que el asistente responde, antes de guardarse en ningún lado."""

    answer: str
    warning: str | None
    abstained: bool
    evidence: list


def evaluate_message(db: Session, message: str) -> Answered:
    """Calcula la respuesta a un mensaje **sin persistir nada**.

    Es el camino que atiende a las usuarias y también el que mide el banco de
    evaluación. Que sea el mismo, y no una copia, es la condición para que la
    medición signifique algo: una copia divergiría en silencio.

    No escribe conversaciones, mensajes ni `AIRun`: evaluar no debe ensuciar las
    conversaciones de nadie.
    """
    normative, terms = _classify(message)
    evidence = _retrieve_published(db, terms)
    answer, warning, abstained = _compose(evidence, normative)
    validate_normative_response(
        is_normative=normative,
        abstained=abstained,
        citation_count=len(evidence),
        warning=warning,
    )
    return Answered(answer=answer, warning=warning, abstained=abstained, evidence=evidence)


def answer_query(db: Session, user: User, payload) -> AssistantQueryResponse:
    """Responde una consulta con evidencia citada o se abstiene.

    `_resolve_conversation` bloquea la fila de la conversación, de modo que dos
    consultas simultáneas sobre la misma conversación se serializan y no chocan
    al calcular `sequence_number`. El reintento cubre cualquier colisión que
    llegue igualmente a la restricción `uq_message_sequence`.
    """
    assert_permission(db, user, "conversation.manage_own")
    for attempt in (1, 2):
        try:
            return _answer_query_once(db, user, payload)
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise Conflict("No se pudo registrar el mensaje; reintente") from None
    raise AssertionError("inalcanzable")


def _answer_query_once(db: Session, user: User, payload) -> AssistantQueryResponse:
    conversation = _resolve_conversation(db, user, payload)
    next_sequence = _next_sequence(db, conversation)
    _persist_user_message(db, conversation, payload.message, next_sequence)

    respuesta = evaluate_message(db, payload.message)
    answer, warning, abstained, evidence = (
        respuesta.answer,
        respuesta.warning,
        respuesta.abstained,
        respuesta.evidence,
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        sequence_number=next_sequence + 1,
        sender="ASSISTANT",
        content_encrypted=encrypt_text(answer),
        content_hash=hashlib.sha256(answer.encode()).hexdigest(),
        moderation_status="WARNED" if warning else "ALLOWED",
    )
    db.add(assistant_message)
    db.flush()

    trace_id = str(uuid4())
    db.add(
        AIRun(
            assistant_message_id=assistant_message.id,
            trace_id=trace_id,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            prompt_policy_version="safe-rag-v1",
            response_status="ABSTAINED" if abstained else "COMPLETED",
            abstained=abstained,
        )
    )
    citations = _persist_citations(db, assistant_message, evidence)
    db.commit()
    return AssistantQueryResponse(
        answer=answer,
        citations=citations,
        warning=warning,
        abstained=abstained,
        trace_id=trace_id,
    )


def _resolve_conversation(db: Session, user: User, payload) -> Conversation:
    """Obtiene la conversación de la usuaria, bloqueada, o crea una nueva."""
    if payload.conversation_id:
        conversation = db.scalar(
            select(Conversation)
            .where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == user.id,
                Conversation.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if conversation is None:
            raise NotFound("Conversación no encontrada")
        return conversation
    if payload.business_id:
        owned_business(db, user, payload.business_id)
    conversation = Conversation(user_id=user.id, business_id=payload.business_id)
    db.add(conversation)
    db.flush()
    return conversation


def _next_sequence(db: Session, conversation: Conversation) -> int:
    current = db.scalar(
        select(func.coalesce(func.max(Message.sequence_number), 0)).where(
            Message.conversation_id == conversation.id
        )
    )
    return (current or 0) + 1


def _persist_user_message(db: Session, conversation: Conversation, message: str, sequence: int) -> None:
    db.add(
        Message(
            conversation_id=conversation.id,
            sequence_number=sequence,
            sender="USER",
            content_encrypted=encrypt_text(message),
            content_hash=hashlib.sha256(message.encode()).hexdigest(),
            moderation_status="ALLOWED",
        )
    )


#: Cuántos términos se llevan a la consulta. El resto de la frase no aporta y
#: alargaría el `AGAINST` sin cambiar el orden.
MAX_TERMS = 8

#: Fragmentos que se citan como mucho.
MAX_EVIDENCE = 3


def _classify(message: str) -> tuple[bool, list[str]]:
    """Extrae los términos de búsqueda y detecta si la consulta es normativa.

    El umbral de cuatro letras es deliberado y coincide con el mínimo del índice:
    `innodb_ft_min_token_size` vale 3, de modo que ninguna palabra que llegue a
    la consulta queda fuera del índice.

    Devuelve los términos **ordenados**: cuando la consulta trae más de
    `MAX_TERMS`, un conjunto sin orden elegiría un subconjunto distinto en cada
    ejecución y la misma pregunta daría respuestas distintas.
    """
    terms = {term for term in re.findall(r"[a-záéíóúñ]+", message.casefold()) if len(term) >= 4}
    return bool(terms & NORMATIVE_TERMS), sorted(terms)


def _retrieve_published(db: Session, terms: list[str]) -> list:
    """Recupera los fragmentos más relevantes de fuentes y versiones publicadas.

    Usa el índice `idx_source_chunks_fulltext`, creado en `0001` y hasta ahora
    sin uso. Frente al `LIKE '%término%'` anterior aporta tres cosas: ordena por
    relevancia en vez de tomar lo primero que devuelva la base, coincide por
    palabra completa y no por subcadena, y descarta las palabras vacías.

    Una consulta sin términos utilizables no recupera nada, y el asistente se
    abstiene. Antes devolvía tres fragmentos cualesquiera, que es peor: citar
    algo que no viene al caso es más engañoso que decir que no se sabe.
    """
    if not terms:
        return []
    relevancia = match(
        SourceChunk.heading,
        SourceChunk.content,
        against=" ".join(terms[:MAX_TERMS]),
        in_natural_language_mode=True,
    )
    query = (
        select(SourceChunk, SourceVersion, Source, SourcePublisher)
        .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
        .join(Source, Source.id == SourceVersion.source_id)
        .join(SourcePublisher, SourcePublisher.id == Source.publisher_id)
        .where(
            SourceVersion.status == "PUBLISHED",
            Source.status == "PUBLISHED",
            relevancia > 0,
        )
        .order_by(relevancia.desc())
        .limit(MAX_EVIDENCE)
    )
    return db.execute(query).all()


def _compose(evidence: list, normative: bool) -> tuple[str, str | None, bool]:
    """Construye la respuesta observable; los textos no cambian respecto de v0.1.0."""
    if not evidence:
        return ABSTENTION_ANSWER, ABSTENTION_WARNING, True
    answer = "Encontré información relacionada en las fuentes verificadas:\n\n" + "\n\n".join(
        f"• {chunk.content[:300].strip()}" for chunk, _, _, _ in evidence
    )
    return answer, NORMATIVE_WARNING if normative else None, False


def _persist_citations(db: Session, assistant_message: Message, evidence: list) -> list[Citation]:
    citations: list[Citation] = []
    for order, (chunk, version, source, publisher) in enumerate(evidence, start=1):
        db.add(
            MessageCitation(
                message_id=assistant_message.id,
                source_version_id=version.id,
                source_chunk_id=chunk.id,
                display_order=order,
                institution_snapshot=publisher.name,
                title_snapshot=source.title,
                url_snapshot=source.canonical_url,
                version_snapshot=version.version_label,
                consulted_at_snapshot=version.consulted_at,
                excerpt_snapshot=chunk.content[:500],
            )
        )
        citations.append(
            Citation(
                source_version_id=version.id,
                source_chunk_id=chunk.id,
                institution=publisher.name,
                title=source.title,
                url=source.canonical_url,
                version_or_date=version.version_label,
                consulted_at=version.consulted_at,
            )
        )
    return citations


def create_feedback(db: Session, user: User, payload) -> dict[str, str]:
    """Registra retroalimentación sobre un mensaje propio del asistente."""
    assert_permission(db, user, "conversation.manage_own")
    message = db.scalar(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == payload.message_id, Conversation.user_id == user.id)
    )
    if message is None:
        raise NotFound("Mensaje no encontrado")
    existing = db.scalar(
        select(ResponseFeedback).where(
            ResponseFeedback.message_id == message.id, ResponseFeedback.user_id == user.id
        )
    )
    if existing:
        raise Conflict("Ya existe retroalimentación")
    feedback = ResponseFeedback(
        message_id=message.id,
        user_id=user.id,
        feedback_type=payload.feedback_type,
        comment_encrypted=encrypt_text(payload.comment) if payload.comment else None,
    )
    db.add(feedback)
    db.commit()
    return {"id": feedback.id}
