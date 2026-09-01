"""Registro, verificación de contacto, inicio de sesión y sesiones."""

import hashlib
import re
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.api_contracts import RegistrationResult, TokenPair
from app.config import get_settings
from app.core.clock import utc_now
from app.core.exceptions import BadRequest, Invalid, TooManyRequests, Unauthorized, Unavailable
from app.models.base import new_uuid7
from app.models.business import UserPreference
from app.models.identity import AuthChallenge, PasswordCredential, Role, Session, User, UserContact, UserRole
from app.models.privacy import ConsentPurpose, ConsentVersion, UserConsent
from app.security import create_access_token, hash_password, hash_token, new_opaque_token, verify_password
from app.services.audit_service import write_audit
from app.services.rate_limit import login_ip_limiter, login_limiter, verification_limiter

settings = get_settings()

#: Mismo texto para un contacto nuevo y para uno ya registrado: la respuesta de
#: `/auth/register` no debe permitir descubrir si una cuenta existe.
REGISTRATION_MESSAGE = "Cuenta creada. Verifique el contacto para activarla."


def _normalize_email(value: str) -> str:
    return value.strip().casefold()


def _normalize_phone(value: str) -> str:
    return re.sub(r"[^0-9+]", "", value.strip())


def normalize_contact(contact_type: str, value: str) -> str:
    """Valida y normaliza un contacto de registro."""
    if contact_type == "EMAIL":
        normalized = _normalize_email(value)
        if "@" not in normalized:
            raise Invalid("Correo inválido")
        return normalized
    phone = _normalize_phone(value)
    if len(phone.replace("+", "")) < 8:
        raise Invalid("Teléfono inválido")
    return phone


def normalize_contact_for_lookup(contact: str) -> str:
    """Normaliza un contacto para buscarlo, infiriendo el tipo y sin validar.

    El inicio de sesión no debe responder 422 ante un contacto mal formado: eso
    distinguiría "formato inválido" de "credenciales incorrectas".
    """
    return _normalize_email(contact) if "@" in contact else _normalize_phone(contact)


def issue_tokens(db: OrmSession, user: User) -> TokenPair:
    """Crea una sesión de refresco y devuelve el par de tokens."""
    refresh = new_opaque_token()
    db.add(
        Session(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh),
            expires_at=utc_now() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


def register(db: OrmSession, payload) -> RegistrationResult:
    """Crea una cuenta pendiente de verificación.

    Si el contacto ya está registrado se devuelve exactamente la misma forma de
    respuesta que para uno nuevo, sin crear nada. `v0.1.0` respondía 409 con el
    texto "El contacto ya está registrado", lo que permitía enumerar cuentas.

    En `development` se sigue devolviendo `verification_token` para el contacto
    nuevo, porque no hay servicio de correo y el frontend completa el alta con
    él. Esa comodidad sí distingue ambos casos, y por eso solo existe en
    desarrollo: en cualquier otro entorno el token nunca viaja en la respuesta.
    """
    if not payload.accept_account_terms:
        raise Invalid("Debe aceptar el consentimiento de cuenta")
    normalized = normalize_contact(payload.contact_type, payload.value)
    expose_token = settings.app_env == "development"

    if db.scalar(select(UserContact).where(UserContact.value_normalized == normalized)):
        return RegistrationResult(
            user_id=new_uuid7(),
            verification_token=None,
            message=REGISTRATION_MESSAGE,
        )

    user = User(status="PENDING")
    db.add(user)
    db.flush()
    contact = UserContact(
        user_id=user.id,
        contact_type=payload.contact_type,
        value_normalized=normalized,
        is_primary=True,
    )
    db.add(contact)
    db.add(
        PasswordCredential(
            user_id=user.id,
            password_hash=hash_password(payload.password),
            password_changed_at=utc_now(),
        )
    )
    db.add(UserPreference(user_id=user.id))
    role = db.scalar(select(Role).where(Role.code == "EMPRENDEDORA"))
    if role is None:
        raise Unavailable("Roles iniciales no disponibles")
    db.add(UserRole(user_id=user.id, role_id=role.id))
    purpose = db.scalar(select(ConsentPurpose).where(ConsentPurpose.code == "ACCOUNT"))
    if purpose:
        version = db.scalar(
            select(ConsentVersion)
            .where(ConsentVersion.purpose_id == purpose.id, ConsentVersion.retired_at.is_(None))
            .order_by(ConsentVersion.published_at.desc())
        )
        if version:
            db.add(
                UserConsent(
                    user_id=user.id,
                    purpose_id=purpose.id,
                    consent_version_id=version.id,
                    decision="GRANTED",
                    decided_at=utc_now(),
                    source="WEB",
                    evidence_hash=hashlib.sha256(f"{user.id}|ACCOUNT|GRANTED".encode()).hexdigest(),
                )
            )
    token = new_opaque_token()
    db.flush()
    db.add(
        AuthChallenge(
            contact_id=contact.id,
            purpose="VERIFY_CONTACT",
            token_hash=hash_token(token),
            expires_at=utc_now() + timedelta(minutes=15),
        )
    )
    write_audit(db, actor=user, action="account.register", object_type="user", object_id=user.id)
    db.commit()
    return RegistrationResult(
        user_id=user.id,
        verification_token=token if expose_token else None,
        message=REGISTRATION_MESSAGE,
    )


def verify_contact(db: OrmSession, payload, *, client_key: str) -> dict[str, str]:
    """Canjea un código de verificación y activa la cuenta."""
    _guard(verification_limiter, client_key)
    challenge = db.scalar(
        select(AuthChallenge).where(
            AuthChallenge.token_hash == hash_token(payload.token),
            AuthChallenge.purpose == "VERIFY_CONTACT",
            AuthChallenge.consumed_at.is_(None),
            AuthChallenge.expires_at > utc_now(),
        )
    )
    if challenge is None:
        verification_limiter.record_failure(client_key)
        raise BadRequest("Código inválido o vencido")
    contact = db.get(UserContact, challenge.contact_id)
    user = db.get(User, contact.user_id if contact else "")
    if contact is None or user is None:
        verification_limiter.record_failure(client_key)
        raise BadRequest("Cuenta no disponible")
    contact.verified_at = utc_now()
    challenge.consumed_at = utc_now()
    user.status = "ACTIVE"
    write_audit(db, actor=user, action="contact.verify", object_type="user_contact", object_id=contact.id)
    db.commit()
    verification_limiter.reset(client_key)
    return {"message": "Contacto verificado; la cuenta está activa"}


def login(db: OrmSession, payload, *, client_key: str) -> TokenPair:
    """Autentica por contacto verificado y contraseña."""
    normalized = normalize_contact_for_lookup(payload.contact)
    contact_key = f"contact:{normalized}"
    _guard(login_limiter, contact_key)
    _guard(login_ip_limiter, client_key)

    contact = db.scalar(
        select(UserContact).where(
            UserContact.value_normalized == normalized,
            UserContact.verified_at.is_not(None),
        )
    )
    credential = db.get(PasswordCredential, contact.user_id) if contact else None
    user = db.get(User, contact.user_id) if contact else None
    if (
        contact is None
        or credential is None
        or user is None
        or user.status != "ACTIVE"
        or not verify_password(credential.password_hash, payload.password)
    ):
        login_limiter.record_failure(contact_key)
        login_ip_limiter.record_failure(client_key)
        if user is not None:
            write_audit(
                db,
                actor=user,
                action="auth.login",
                object_type="user",
                object_id=user.id,
                result="FAILED",
            )
            db.commit()
        raise Unauthorized("Credenciales inválidas")

    user.last_login_at = utc_now()
    tokens = issue_tokens(db, user)
    write_audit(db, actor=user, action="auth.login", object_type="user", object_id=user.id)
    db.commit()
    # Solo se reinicia el contador del contacto. El de la IP no se reinicia: si
    # bastara con un acceso correcto para limpiarlo, quien tenga una cuenta
    # propia podría rociar contraseñas contra el resto sin tope.
    login_limiter.reset(contact_key)
    return tokens


def refresh(db: OrmSession, payload) -> TokenPair:
    """Rota la sesión: revoca el token presentado y emite uno nuevo."""
    session = db.scalar(
        select(Session).where(
            Session.refresh_token_hash == hash_token(payload.refresh_token),
            Session.revoked_at.is_(None),
            Session.expires_at > utc_now(),
        )
    )
    if session is None:
        raise Unauthorized("Sesión inválida o vencida")
    user = db.get(User, session.user_id)
    if user is None or user.status != "ACTIVE":
        raise Unauthorized("Cuenta no disponible")
    session.revoked_at = utc_now()
    tokens = issue_tokens(db, user)
    db.commit()
    return tokens


def logout(db: OrmSession, payload, user: User) -> dict[str, str]:
    """Revoca la sesión indicada por el token de refresco."""
    session = db.scalar(
        select(Session).where(
            Session.user_id == user.id,
            Session.refresh_token_hash == hash_token(payload.refresh_token),
            Session.revoked_at.is_(None),
        )
    )
    if session:
        session.revoked_at = utc_now()
    write_audit(db, actor=user, action="auth.logout", object_type="user", object_id=user.id)
    db.commit()
    return {"message": "Sesión cerrada"}


def _guard(limiter, key: str) -> None:
    retry_after = limiter.retry_after(key)
    if retry_after:
        raise TooManyRequests(f"Demasiados intentos. Reintente en {retry_after} segundos.")
