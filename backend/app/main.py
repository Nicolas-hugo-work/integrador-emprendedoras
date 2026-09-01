import hashlib
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select

from app.api_contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    BusinessCreate,
    BusinessView,
    Citation,
    ConsentDecision,
    ContactRegistration,
    ConversationCreate,
    ConversationView,
    CostItemCreate,
    DeleteAccountRequest,
    FeedbackCreate,
    FinancialMovementCreate,
    FinancialMovementView,
    LoginRequest,
    PricingScenarioCreate,
    RefreshRequest,
    RegistrationResult,
    SourceChunkCreate,
    SourceCreate,
    SourceVersionCreate,
    TokenPair,
    UserView,
    VerifyContactRequest,
)
from app.config import get_settings
from app.dependencies import DB, CurrentUser
from app.domain_rules import (
    account_purge_deadline,
    calculate_suggested_price,
    validate_normative_response,
    validate_transfer,
)
from app.models.admin_research import AuditEvent
from app.models.business import Business, BusinessMembership, UserPreference
from app.models.conversation import AIRun, Conversation, Message, MessageCitation, ResponseFeedback
from app.models.finance import (
    CostItem,
    FinancialCategory,
    FinancialMovement,
    PricingScenario,
    PricingScenarioCost,
)
from app.models.identity import (
    AuthChallenge,
    PasswordCredential,
    Permission,
    Role,
    RolePermission,
    Session,
    User,
    UserContact,
    UserRole,
)
from app.models.privacy import (
    ConsentPurpose,
    ConsentVersion,
    DataExportRequest,
    DeletionRequest,
    UserConsent,
)
from app.models.rag import Source, SourceChunk, SourcePublisher, SourceVersion
from app.security import (
    create_access_token,
    decrypt_text,
    encrypt_text,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NORMATIVE_TERMS = {
    "nit", "impuesto", "tributario", "tributaria", "seprec", "formalización",
    "formalizacion", "registro", "ley", "normativa", "trámite", "tramite",
}


def utc_now() -> datetime:
    return datetime.utcnow()


def normalize_contact(contact_type: str, value: str) -> str:
    value = value.strip()
    if contact_type == "EMAIL":
        if "@" not in value:
            raise HTTPException(status_code=422, detail="Correo inválido")
        return value.casefold()
    phone = re.sub(r"[^0-9+]", "", value)
    if len(phone.replace("+", "")) < 8:
        raise HTTPException(status_code=422, detail="Teléfono inválido")
    return phone


def write_audit(
    db: DB, *, actor: User | None, action: str, object_type: str,
    object_id: str | None, result: str = "SUCCESS",
) -> None:
    occurred_at = utc_now()
    pseudonym = hashlib.sha256((actor.id if actor else "system").encode()).hexdigest()[:32]
    raw = f"{pseudonym}|{action}|{object_type}|{object_id}|{occurred_at.isoformat()}|{result}"
    db.add(AuditEvent(
        actor_user_id=actor.id if actor else None,
        actor_pseudonym=pseudonym,
        action=action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        occurred_at=occurred_at,
        correlation_id=str(uuid4()),
        integrity_hash=hashlib.sha256(raw.encode()).hexdigest(),
    ))


def assert_permission(db: DB, user: User, permission_code: str) -> None:
    allowed = db.scalar(
        select(func.count()).select_from(UserRole)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == user.id, Permission.code == permission_code)
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Permiso insuficiente")


def owned_business(db: DB, user: User, business_id: str) -> Business:
    business = db.scalar(select(Business).where(
        Business.id == business_id,
        Business.owner_user_id == user.id,
        Business.deleted_at.is_(None),
    ))
    if business is None:
        raise HTTPException(status_code=404, detail="Emprendimiento no encontrado")
    return business


def issue_tokens(db: DB, user: User) -> TokenPair:
    refresh = new_opaque_token()
    db.add(Session(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_ttl_days),
    ))
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pwa-autonomia-backend"}


@app.post("/auth/register", response_model=RegistrationResult, status_code=201, tags=["auth"])
def register(payload: ContactRegistration, db: DB) -> RegistrationResult:
    if not payload.accept_account_terms:
        raise HTTPException(status_code=422, detail="Debe aceptar el consentimiento de cuenta")
    normalized = normalize_contact(payload.contact_type, payload.value)
    if db.scalar(select(UserContact).where(UserContact.value_normalized == normalized)):
        raise HTTPException(status_code=409, detail="El contacto ya está registrado")
    user = User(status="PENDING")
    db.add(user)
    db.flush()
    contact = UserContact(
        user_id=user.id, contact_type=payload.contact_type,
        value_normalized=normalized, is_primary=True,
    )
    db.add(contact)
    db.add(PasswordCredential(
        user_id=user.id, password_hash=hash_password(payload.password),
        password_changed_at=utc_now(),
    ))
    db.add(UserPreference(user_id=user.id))
    role = db.scalar(select(Role).where(Role.code == "EMPRENDEDORA"))
    if role is None:
        raise HTTPException(status_code=500, detail="Roles iniciales no disponibles")
    db.add(UserRole(user_id=user.id, role_id=role.id))
    purpose = db.scalar(select(ConsentPurpose).where(ConsentPurpose.code == "ACCOUNT"))
    if purpose:
        version = db.scalar(
            select(ConsentVersion)
            .where(ConsentVersion.purpose_id == purpose.id, ConsentVersion.retired_at.is_(None))
            .order_by(ConsentVersion.published_at.desc())
        )
        if version:
            db.add(UserConsent(
                user_id=user.id, purpose_id=purpose.id, consent_version_id=version.id,
                decision="GRANTED", decided_at=utc_now(), source="WEB",
                evidence_hash=hashlib.sha256(f"{user.id}|ACCOUNT|GRANTED".encode()).hexdigest(),
            ))
    token = new_opaque_token()
    db.flush()
    db.add(AuthChallenge(
        contact_id=contact.id, purpose="VERIFY_CONTACT", token_hash=hash_token(token),
        expires_at=utc_now() + timedelta(minutes=15),
    ))
    write_audit(db, actor=user, action="account.register", object_type="user", object_id=user.id)
    db.commit()
    return RegistrationResult(
        user_id=user.id,
        verification_token=token if settings.app_env == "development" else None,
        message="Cuenta creada. Verifique el contacto para activarla.",
    )


@app.post("/auth/verify-contact", tags=["auth"])
def verify_contact(payload: VerifyContactRequest, db: DB) -> dict[str, str]:
    challenge = db.scalar(select(AuthChallenge).where(
        AuthChallenge.token_hash == hash_token(payload.token),
        AuthChallenge.purpose == "VERIFY_CONTACT",
        AuthChallenge.consumed_at.is_(None),
        AuthChallenge.expires_at > utc_now(),
    ))
    if challenge is None:
        raise HTTPException(status_code=400, detail="Código inválido o vencido")
    contact = db.get(UserContact, challenge.contact_id)
    user = db.get(User, contact.user_id if contact else "")
    if contact is None or user is None:
        raise HTTPException(status_code=400, detail="Cuenta no disponible")
    contact.verified_at = utc_now()
    challenge.consumed_at = utc_now()
    user.status = "ACTIVE"
    write_audit(db, actor=user, action="contact.verify", object_type="user_contact", object_id=contact.id)
    db.commit()
    return {"message": "Contacto verificado; la cuenta está activa"}


@app.post("/auth/login", response_model=TokenPair, tags=["auth"])
def login(payload: LoginRequest, db: DB) -> TokenPair:
    normalized = payload.contact.casefold().strip() if "@" in payload.contact else re.sub(
        r"[^0-9+]", "", payload.contact
    )
    contact = db.scalar(select(UserContact).where(
        UserContact.value_normalized == normalized, UserContact.verified_at.is_not(None)
    ))
    if contact is None:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    credential = db.get(PasswordCredential, contact.user_id)
    user = db.get(User, contact.user_id)
    if credential is None or user is None or user.status != "ACTIVE" or not verify_password(
        credential.password_hash, payload.password
    ):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    user.last_login_at = utc_now()
    tokens = issue_tokens(db, user)
    write_audit(db, actor=user, action="auth.login", object_type="user", object_id=user.id)
    db.commit()
    return tokens


@app.post("/auth/refresh", response_model=TokenPair, tags=["auth"])
def refresh(payload: RefreshRequest, db: DB) -> TokenPair:
    session = db.scalar(select(Session).where(
        Session.refresh_token_hash == hash_token(payload.refresh_token),
        Session.revoked_at.is_(None), Session.expires_at > utc_now(),
    ))
    if session is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida")
    user = db.get(User, session.user_id)
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Cuenta no disponible")
    session.revoked_at = utc_now()
    tokens = issue_tokens(db, user)
    db.commit()
    return tokens


@app.post("/auth/logout", tags=["auth"])
def logout(payload: RefreshRequest, db: DB, user: CurrentUser) -> dict[str, str]:
    session = db.scalar(select(Session).where(
        Session.user_id == user.id,
        Session.refresh_token_hash == hash_token(payload.refresh_token),
        Session.revoked_at.is_(None),
    ))
    if session:
        session.revoked_at = utc_now()
    write_audit(db, actor=user, action="auth.logout", object_type="user", object_id=user.id)
    db.commit()
    return {"message": "Sesión cerrada"}


@app.get("/me", response_model=UserView, tags=["account"])
def me(user: CurrentUser) -> User:
    return user


@app.post("/businesses", response_model=BusinessView, status_code=201, tags=["businesses"])
def create_business(payload: BusinessCreate, db: DB, user: CurrentUser) -> Business:
    business = Business(owner_user_id=user.id, **payload.model_dump())
    db.add(business)
    db.flush()
    db.add(BusinessMembership(business_id=business.id, user_id=user.id, member_role="OWNER"))
    write_audit(db, actor=user, action="business.create", object_type="business", object_id=business.id)
    db.commit()
    db.refresh(business)
    return business


@app.get("/businesses", response_model=list[BusinessView], tags=["businesses"])
def list_businesses(db: DB, user: CurrentUser) -> list[Business]:
    return list(db.scalars(select(Business).where(
        Business.owner_user_id == user.id, Business.deleted_at.is_(None)
    ).order_by(Business.created_at.desc())))


@app.post("/finance/movements", response_model=FinancialMovementView, status_code=201, tags=["finance"])
def create_movement(payload: FinancialMovementCreate, db: DB, user: CurrentUser) -> FinancialMovementView:
    validate_transfer(payload.movement_type, payload.scope, payload.counter_scope)
    if payload.business_id:
        owned_business(db, user, payload.business_id)
    elif payload.scope == "BUSINESS":
        raise HTTPException(status_code=422, detail="Un movimiento del negocio requiere business_id")
    category = db.get(FinancialCategory, payload.category_id)
    if category is None or category.movement_type != payload.movement_type:
        raise HTTPException(status_code=422, detail="Categoría incompatible con el movimiento")
    movement = FinancialMovement(
        user_id=user.id, business_id=payload.business_id, category_id=payload.category_id,
        movement_type=payload.movement_type, scope=payload.scope,
        counter_scope=payload.counter_scope, amount=payload.amount,
        currency=payload.currency, occurred_on=payload.occurred_on,
        note_encrypted=encrypt_text(payload.note) if payload.note else None,
    )
    db.add(movement)
    db.flush()
    write_audit(db, actor=user, action="finance.create", object_type="financial_movement", object_id=movement.id)
    db.commit()
    return FinancialMovementView(
        id=movement.id, business_id=movement.business_id, category_id=movement.category_id,
        movement_type=movement.movement_type, scope=movement.scope,
        counter_scope=movement.counter_scope, amount=movement.amount,
        currency=movement.currency, occurred_on=movement.occurred_on,
        note=decrypt_text(movement.note_encrypted) if movement.note_encrypted else None,
    )


@app.get("/finance/categories", tags=["finance"])
def list_financial_categories(db: DB, user: CurrentUser) -> list[dict[str, str]]:
    rows = db.scalars(select(FinancialCategory).order_by(
        FinancialCategory.movement_type, FinancialCategory.name
    )).all()
    return [
        {"id": row.id, "code": row.code, "name": row.name, "movement_type": row.movement_type}
        for row in rows
    ]


@app.get("/finance/movements", response_model=list[FinancialMovementView], tags=["finance"])
def list_movements(
    db: DB, user: CurrentUser, business_id: str | None = None,
    date_from: date | None = None, date_to: date | None = None,
) -> list[FinancialMovementView]:
    query = select(FinancialMovement).where(
        FinancialMovement.user_id == user.id, FinancialMovement.deleted_at.is_(None)
    )
    if business_id:
        owned_business(db, user, business_id)
        query = query.where(FinancialMovement.business_id == business_id)
    if date_from:
        query = query.where(FinancialMovement.occurred_on >= date_from)
    if date_to:
        query = query.where(FinancialMovement.occurred_on <= date_to)
    return [FinancialMovementView(
        id=row.id, business_id=row.business_id, category_id=row.category_id,
        movement_type=row.movement_type, scope=row.scope, counter_scope=row.counter_scope,
        amount=row.amount, currency=row.currency, occurred_on=row.occurred_on,
        note=decrypt_text(row.note_encrypted) if row.note_encrypted else None,
    ) for row in db.scalars(query.order_by(FinancialMovement.occurred_on.desc())).all()]


@app.post("/finance/costs", status_code=201, tags=["finance"])
def create_cost(payload: CostItemCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    owned_business(db, user, payload.business_id)
    cost = CostItem(
        business_id=payload.business_id, name=payload.name, cost_type=payload.cost_type,
        amount=payload.amount, currency=payload.currency, unit=payload.unit,
        periodicity=payload.periodicity, quantity_base=payload.quantity_base,
        notes_encrypted=encrypt_text(payload.notes) if payload.notes else None,
    )
    db.add(cost)
    db.commit()
    return {"id": cost.id}


@app.post("/finance/pricing", tags=["finance"])
def create_pricing_scenario(payload: PricingScenarioCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    owned_business(db, user, payload.business_id)
    costs = list(db.scalars(select(CostItem).where(
        CostItem.business_id == payload.business_id,
        CostItem.id.in_(payload.cost_item_ids), CostItem.deleted_at.is_(None),
    )))
    if len(costs) != len(set(payload.cost_item_ids)):
        raise HTTPException(status_code=422, detail="Uno o más costos no existen")
    unit_cost, suggested = calculate_suggested_price(
        [item.amount for item in costs], payload.units, payload.margin_percent
    )
    scenario = PricingScenario(
        business_id=payload.business_id, created_by_user_id=user.id,
        product_name=payload.product_name, units=payload.units,
        margin_percent=payload.margin_percent, unit_cost=unit_cost,
        suggested_price=suggested, currency=payload.currency,
        formula_version="simple-v1", assumptions={"cost_count": len(costs)},
    )
    db.add(scenario)
    db.flush()
    for item in costs:
        db.add(PricingScenarioCost(
            scenario_id=scenario.id, cost_item_id=item.id, label_snapshot=item.name,
            amount_snapshot=item.amount, allocation_quantity=item.quantity_base,
        ))
    db.commit()
    return {"id": scenario.id, "unit_cost": str(unit_cost), "suggested_price": str(suggested)}


@app.get("/finance/summary", tags=["finance"])
def financial_summary(
    db: DB, user: CurrentUser, business_id: str,
    date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
) -> dict[str, str]:
    owned_business(db, user, business_id)
    query = select(FinancialMovement).where(
        FinancialMovement.user_id == user.id,
        FinancialMovement.business_id == business_id,
        FinancialMovement.deleted_at.is_(None),
    )
    if date_from:
        query = query.where(FinancialMovement.occurred_on >= date_from)
    if date_to:
        query = query.where(FinancialMovement.occurred_on <= date_to)
    income, outflow = Decimal("0"), Decimal("0")
    for movement in db.scalars(query):
        if movement.movement_type == "INCOME":
            income += movement.amount
        elif movement.movement_type in {"EXPENSE", "COST"}:
            outflow += movement.amount
    return {"income": str(income), "outflow": str(outflow), "balance": str(income - outflow)}


@app.post("/conversations", response_model=ConversationView, status_code=201, tags=["assistant"])
def create_conversation(payload: ConversationCreate, db: DB, user: CurrentUser) -> ConversationView:
    if payload.business_id:
        owned_business(db, user, payload.business_id)
    conversation = Conversation(
        user_id=user.id, business_id=payload.business_id,
        title_encrypted=encrypt_text(payload.title) if payload.title else None,
        topic_code=payload.topic_code,
    )
    db.add(conversation)
    db.commit()
    return ConversationView(
        id=conversation.id, business_id=conversation.business_id,
        title=decrypt_text(conversation.title_encrypted) if conversation.title_encrypted else None,
        topic_code=conversation.topic_code, status=conversation.status,
        updated_at=conversation.updated_at,
    )


@app.get("/conversations", response_model=list[ConversationView], tags=["assistant"])
def list_conversations(db: DB, user: CurrentUser) -> list[ConversationView]:
    rows = db.scalars(select(Conversation).where(
        Conversation.user_id == user.id, Conversation.deleted_at.is_(None)
    ).order_by(Conversation.updated_at.desc())).all()
    return [ConversationView(
        id=row.id, business_id=row.business_id,
        title=decrypt_text(row.title_encrypted) if row.title_encrypted else None,
        topic_code=row.topic_code, status=row.status, updated_at=row.updated_at,
    ) for row in rows]


@app.post("/assistant/query", response_model=AssistantQueryResponse, tags=["assistant"])
def assistant_query(payload: AssistantQueryRequest, db: DB, user: CurrentUser) -> AssistantQueryResponse:
    if payload.conversation_id:
        conversation = db.scalar(select(Conversation).where(
            Conversation.id == payload.conversation_id,
            Conversation.user_id == user.id, Conversation.deleted_at.is_(None),
        ))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    else:
        if payload.business_id:
            owned_business(db, user, payload.business_id)
        conversation = Conversation(user_id=user.id, business_id=payload.business_id)
        db.add(conversation)
        db.flush()
    next_sequence = (db.scalar(select(func.coalesce(func.max(Message.sequence_number), 0)).where(
        Message.conversation_id == conversation.id
    )) or 0) + 1
    db.add(Message(
        conversation_id=conversation.id, sequence_number=next_sequence, sender="USER",
        content_encrypted=encrypt_text(payload.message),
        content_hash=hashlib.sha256(payload.message.encode()).hexdigest(),
        moderation_status="ALLOWED",
    ))
    terms = {term for term in re.findall(r"[a-záéíóúñ]+", payload.message.casefold()) if len(term) >= 4}
    normative = bool(terms & NORMATIVE_TERMS)
    conditions = [SourceChunk.content.like(f"%{term}%") for term in list(terms)[:8]]
    query = (
        select(SourceChunk, SourceVersion, Source, SourcePublisher)
        .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
        .join(Source, Source.id == SourceVersion.source_id)
        .join(SourcePublisher, SourcePublisher.id == Source.publisher_id)
        .where(SourceVersion.status == "PUBLISHED", Source.status == "PUBLISHED")
        .limit(3)
    )
    if conditions:
        query = query.where(or_(*conditions))
    evidence = db.execute(query).all()
    warning = None
    abstained = not bool(evidence)
    if evidence:
        answer = "Encontré información relacionada en las fuentes verificadas:\n\n" + "\n\n".join(
            f"• {chunk.content[:300].strip()}" for chunk, _, _, _ in evidence
        )
        if normative:
            warning = (
                "Información educativa sujeta a cambios. Verifique la vigencia en la fuente "
                "oficial o consulte a una persona profesional competente."
            )
    else:
        answer = (
            "No encontré evidencia suficiente en las fuentes publicadas para responder con seguridad. "
            "Puedes reformular la consulta o revisar los enlaces oficiales disponibles."
        )
        warning = "El sistema se abstuvo para evitar información inventada o desactualizada."
    validate_normative_response(
        is_normative=normative, abstained=abstained,
        citation_count=len(evidence), warning=warning,
    )
    assistant_message = Message(
        conversation_id=conversation.id, sequence_number=next_sequence + 1,
        sender="ASSISTANT", content_encrypted=encrypt_text(answer),
        content_hash=hashlib.sha256(answer.encode()).hexdigest(),
        moderation_status="WARNED" if warning else "ALLOWED",
    )
    db.add(assistant_message)
    db.flush()
    trace_id = str(uuid4())
    db.add(AIRun(
        assistant_message_id=assistant_message.id, trace_id=trace_id,
        model_name="retrieval-only-mvp", model_version="v1",
        prompt_policy_version="safe-rag-v1",
        response_status="ABSTAINED" if abstained else "COMPLETED",
        abstained=abstained,
    ))
    citations: list[Citation] = []
    for order, (chunk, version, source, publisher) in enumerate(evidence, start=1):
        db.add(MessageCitation(
            message_id=assistant_message.id, source_version_id=version.id,
            source_chunk_id=chunk.id, display_order=order,
            institution_snapshot=publisher.name, title_snapshot=source.title,
            url_snapshot=source.canonical_url, version_snapshot=version.version_label,
            consulted_at_snapshot=version.consulted_at, excerpt_snapshot=chunk.content[:500],
        ))
        citations.append(Citation(
            source_version_id=version.id, source_chunk_id=chunk.id,
            institution=publisher.name, title=source.title, url=source.canonical_url,
            version_or_date=version.version_label, consulted_at=version.consulted_at,
        ))
    db.commit()
    return AssistantQueryResponse(
        answer=answer, citations=citations, warning=warning,
        abstained=abstained, trace_id=trace_id,
    )


@app.post("/feedback", status_code=201, tags=["assistant"])
def create_feedback(payload: FeedbackCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    message = db.scalar(select(Message).join(
        Conversation, Conversation.id == Message.conversation_id
    ).where(Message.id == payload.message_id, Conversation.user_id == user.id))
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    if db.scalar(select(ResponseFeedback).where(
        ResponseFeedback.message_id == message.id, ResponseFeedback.user_id == user.id
    )):
        raise HTTPException(status_code=409, detail="Ya existe retroalimentación")
    feedback = ResponseFeedback(
        message_id=message.id, user_id=user.id, feedback_type=payload.feedback_type,
        comment_encrypted=encrypt_text(payload.comment) if payload.comment else None,
    )
    db.add(feedback)
    db.commit()
    return {"id": feedback.id}


@app.post("/consents", status_code=201, tags=["privacy"])
def decide_consent(payload: ConsentDecision, db: DB, user: CurrentUser) -> dict[str, str]:
    purpose = db.scalar(select(ConsentPurpose).where(ConsentPurpose.code == payload.purpose_code))
    if purpose is None:
        raise HTTPException(status_code=404, detail="Finalidad no encontrada")
    version = db.scalar(select(ConsentVersion).where(
        ConsentVersion.purpose_id == purpose.id,
        ConsentVersion.version == payload.version, ConsentVersion.retired_at.is_(None),
    ))
    if version is None:
        raise HTTPException(status_code=409, detail="Versión no vigente")
    event = UserConsent(
        user_id=user.id, purpose_id=purpose.id, consent_version_id=version.id,
        decision=payload.decision, decided_at=utc_now(), source="WEB",
        evidence_hash=hashlib.sha256(
            f"{user.id}|{purpose.code}|{payload.decision}|{version.notice_hash}".encode()
        ).hexdigest(),
    )
    db.add(event)
    db.flush()
    write_audit(db, actor=user, action="consent.decide", object_type="user_consent", object_id=event.id)
    db.commit()
    return {"id": event.id, "decision": event.decision}


@app.post("/privacy/deletion", status_code=202, tags=["privacy"])
def request_account_deletion(
    payload: DeleteAccountRequest, db: DB, user: CurrentUser,
) -> dict[str, str]:
    requested_at = utc_now()
    deletion = DeletionRequest(
        user_id=user.id, requested_at=requested_at,
        purge_due_at=account_purge_deadline(requested_at),
        status="PENDING", scope="ACCOUNT",
    )
    db.add(deletion)
    user.status = "DELETED"
    user.deleted_at = requested_at
    write_audit(db, actor=user, action="account.delete_request", object_type="user", object_id=user.id)
    db.commit()
    return {"request_id": deletion.id, "purge_due_at": deletion.purge_due_at.isoformat()}


@app.post("/privacy/export", status_code=202, tags=["privacy"])
def request_data_export(db: DB, user: CurrentUser) -> dict[str, str]:
    export = DataExportRequest(user_id=user.id, format="JSON", status="PENDING")
    db.add(export)
    db.flush()
    write_audit(
        db,
        actor=user,
        action="account.export_request",
        object_type="data_export_request",
        object_id=export.id,
    )
    db.commit()
    return {"request_id": export.id, "status": export.status}


@app.post("/sources", status_code=201, tags=["rag-admin"])
def create_source(payload: SourceCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    assert_permission(db, user, "source.review")
    if db.get(SourcePublisher, payload.publisher_id) is None:
        raise HTTPException(status_code=422, detail="Institución emisora no encontrada")
    source = Source(
        publisher_id=payload.publisher_id, title=payload.title,
        canonical_url=str(payload.canonical_url), jurisdiction=payload.jurisdiction,
        topic=payload.topic, license_name=payload.license_name, status="DRAFT",
    )
    db.add(source)
    db.flush()
    write_audit(db, actor=user, action="source.create", object_type="source", object_id=source.id)
    db.commit()
    return {"id": source.id}


@app.post("/source-versions", status_code=201, tags=["rag-admin"])
def create_source_version(payload: SourceVersionCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    assert_permission(db, user, "source.review")
    if db.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    version = SourceVersion(
        source_id=payload.source_id, version_label=payload.version_label,
        publication_date=payload.publication_date, consulted_at=utc_now(),
        valid_from=payload.valid_from, valid_to=payload.valid_to,
        content_hash=payload.content_hash, storage_key=payload.storage_key, status="REVIEW",
    )
    db.add(version)
    db.commit()
    return {"id": version.id, "status": version.status}


@app.post("/source-chunks", status_code=201, tags=["rag-admin"])
def create_source_chunk(payload: SourceChunkCreate, db: DB, user: CurrentUser) -> dict[str, str]:
    assert_permission(db, user, "source.review")
    if db.get(SourceVersion, payload.source_version_id) is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    chunk = SourceChunk(
        source_version_id=payload.source_version_id, chunk_number=payload.chunk_number,
        heading=payload.heading, content=payload.content,
        content_hash=hashlib.sha256(payload.content.encode()).hexdigest(),
        page_number=payload.page_number, token_count=payload.token_count,
    )
    db.add(chunk)
    db.commit()
    return {"id": chunk.id}


@app.post("/source-versions/{version_id}/publish", tags=["rag-admin"])
def publish_source_version(version_id: str, db: DB, user: CurrentUser) -> dict[str, str]:
    assert_permission(db, user, "source.publish")
    version = db.get(SourceVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    chunk_count = db.scalar(select(func.count()).select_from(SourceChunk).where(
        SourceChunk.source_version_id == version.id
    ))
    if not chunk_count:
        raise HTTPException(status_code=409, detail="No se puede publicar sin fragmentos")
    source = db.get(Source, version.source_id)
    version.status = "PUBLISHED"
    if source:
        source.status = "PUBLISHED"
    write_audit(db, actor=user, action="source.publish", object_type="source_version", object_id=version.id)
    db.commit()
    return {"id": version.id, "status": version.status}
