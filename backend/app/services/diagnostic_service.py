"""Diagnóstico educativo y ruta de formalización. Sin LLM."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_contracts import (
    QUESTIONNAIRE_VERSION,
    DiagnosticAnswerView,
    DiagnosticQuestion,
    DiagnosticSessionView,
    FormalizationRouteView,
    FormalizationStepView,
)
from app.core.clock import utc_now
from app.core.exceptions import Conflict, Invalid, NotFound
from app.models.business import DiagnosticAnswer, DiagnosticSession, FormalizationRoute, FormalizationStep
from app.models.identity import User
from app.models.rag import Source, SourceVersion
from app.security import decrypt_text, encrypt_text
from app.services.audit_service import write_audit
from app.services.authorization import assert_permission, owned_business

QUESTIONS: tuple[DiagnosticQuestion, ...] = (
    DiagnosticQuestion(code="ACTIVITY", prompt="¿A qué se dedica tu emprendimiento?"),
    DiagnosticQuestion(code="STAGE", prompt="¿En qué etapa está hoy?"),
    DiagnosticQuestion(
        code="FORMAL",
        prompt="¿Ya tienes NIT o registro de comercio? Cuéntanos con tus palabras.",
    ),
)

_STEPS = (
    (
        "Reunir documentos personales",
        "Ten a mano cédula vigente y un comprobante de domicilio. No pedimos que los subas aquí.",
    ),
    (
        "Consultar el registro de comercio",
        "Revisa en la fuente oficial qué trámites pide SEPREC para tu tipo de actividad.",
    ),
    (
        "Definir el régimen tributario",
        "Compara las opciones vigentes en impuestos nacionales antes de inscribirte. Es orientación, no asesoría.",
    ),
)


def list_questions(db: Session, user: User) -> list[DiagnosticQuestion]:
    assert_permission(db, user, "business.manage_own")
    return list(QUESTIONS)


def _session_view(db: Session, row: DiagnosticSession) -> DiagnosticSessionView:
    answers = db.scalars(
        select(DiagnosticAnswer).where(DiagnosticAnswer.session_id == row.id)
    ).all()
    return DiagnosticSessionView(
        id=row.id,
        business_id=row.business_id,
        questionnaire_version=row.questionnaire_version,
        status=row.status,
        answers=[
            DiagnosticAnswerView(
                question_code=item.question_code,
                answer_text=decrypt_text(item.answer_text_encrypted),
            )
            for item in answers
        ],
        completed_at=row.completed_at,
    )


def _route_view(db: Session, row: FormalizationRoute) -> FormalizationRouteView:
    steps = db.scalars(
        select(FormalizationStep)
        .where(FormalizationStep.route_id == row.id)
        .order_by(FormalizationStep.step_number)
    ).all()
    return FormalizationRouteView(
        id=row.id,
        business_id=row.business_id,
        status=row.status,
        steps=[
            FormalizationStepView(
                id=step.id,
                step_number=step.step_number,
                title=step.title,
                description=step.description,
                source_version_id=step.source_version_id,
                completed_at=step.completed_at,
            )
            for step in steps
        ],
    )


def _owned_session(db: Session, user: User, session_id: str) -> DiagnosticSession:
    row = db.get(DiagnosticSession, session_id)
    if row is None:
        raise NotFound("Diagnóstico no encontrado")
    owned_business(db, user, row.business_id)
    return row


def start_session(db: Session, user: User, payload) -> DiagnosticSessionView:
    assert_permission(db, user, "business.manage_own")
    owned_business(db, user, payload.business_id)
    row = DiagnosticSession(
        business_id=payload.business_id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
        status="IN_PROGRESS",
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        actor=user,
        action="diagnostic.start",
        object_type="diagnostic_session",
        object_id=row.id,
    )
    db.commit()
    return _session_view(db, row)


def get_session(db: Session, user: User, session_id: str) -> DiagnosticSessionView:
    assert_permission(db, user, "business.manage_own")
    return _session_view(db, _owned_session(db, user, session_id))


def save_answer(db: Session, user: User, session_id: str, payload) -> DiagnosticSessionView:
    assert_permission(db, user, "business.manage_own")
    row = _owned_session(db, user, session_id)
    if row.status != "IN_PROGRESS":
        raise Conflict("Este diagnóstico ya no admite respuestas")
    codes = {item.code for item in QUESTIONS}
    if payload.question_code not in codes:
        raise Invalid("Pregunta desconocida")
    existing = db.scalar(
        select(DiagnosticAnswer).where(
            DiagnosticAnswer.session_id == row.id,
            DiagnosticAnswer.question_code == payload.question_code,
        )
    )
    cipher = encrypt_text(payload.answer_text)
    if existing:
        existing.answer_text_encrypted = cipher
    else:
        db.add(
            DiagnosticAnswer(
                session_id=row.id,
                question_code=payload.question_code,
                answer_text_encrypted=cipher,
            )
        )
    db.commit()
    return _session_view(db, row)


def _latest_published_version(db: Session) -> str | None:
    return db.scalar(
        select(SourceVersion.id)
        .join(Source, Source.id == SourceVersion.source_id)
        .where(SourceVersion.status == "PUBLISHED", Source.status == "PUBLISHED")
        .order_by(SourceVersion.created_at.desc())
        .limit(1)
    )


def complete_session(db: Session, user: User, session_id: str) -> FormalizationRouteView:
    assert_permission(db, user, "business.manage_own")
    row = _owned_session(db, user, session_id)
    if row.status == "COMPLETED":
        existing = db.scalar(
            select(FormalizationRoute)
            .where(FormalizationRoute.business_id == row.business_id)
            .order_by(FormalizationRoute.created_at.desc())
        )
        if existing:
            return _route_view(db, existing)
    answered = {
        item.question_code
        for item in db.scalars(
            select(DiagnosticAnswer).where(DiagnosticAnswer.session_id == row.id)
        )
    }
    missing = [item.code for item in QUESTIONS if item.code not in answered]
    if missing:
        raise Conflict("Faltan respuestas: " + ", ".join(missing))
    row.status = "COMPLETED"
    row.completed_at = utc_now()
    route = FormalizationRoute(business_id=row.business_id, status="ACTIVE")
    db.add(route)
    db.flush()
    source_version_id = _latest_published_version(db)
    for number, (title, description) in enumerate(_STEPS, start=1):
        db.add(
            FormalizationStep(
                route_id=route.id,
                step_number=number,
                title=title,
                description=description,
                source_version_id=source_version_id,
            )
        )
    write_audit(
        db,
        actor=user,
        action="diagnostic.complete",
        object_type="formalization_route",
        object_id=route.id,
    )
    db.commit()
    return _route_view(db, route)


def list_routes(db: Session, user: User, business_id: str) -> list[FormalizationRouteView]:
    assert_permission(db, user, "business.manage_own")
    owned_business(db, user, business_id)
    rows = db.scalars(
        select(FormalizationRoute)
        .where(FormalizationRoute.business_id == business_id)
        .order_by(FormalizationRoute.created_at.desc())
    ).all()
    return [_route_view(db, row) for row in rows]


def complete_step(db: Session, user: User, step_id: str) -> FormalizationRouteView:
    assert_permission(db, user, "business.manage_own")
    step = db.get(FormalizationStep, step_id)
    if step is None:
        raise NotFound("Paso no encontrado")
    route = db.get(FormalizationRoute, step.route_id)
    if route is None:
        raise NotFound("Ruta no encontrada")
    owned_business(db, user, route.business_id)
    if step.completed_at is None:
        step.completed_at = utc_now()
    pending = db.scalars(
        select(FormalizationStep).where(
            FormalizationStep.route_id == route.id,
            FormalizationStep.completed_at.is_(None),
        )
    ).all()
    if not pending:
        route.status = "COMPLETED"
    db.commit()
    return _route_view(db, route)
