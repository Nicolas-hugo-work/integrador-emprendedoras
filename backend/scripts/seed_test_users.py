"""Crea cuentas locales de prueba, una por cada rol del sistema."""

import argparse
import hashlib
import os

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.base import utc_now
from app.models.business import UserPreference
from app.models.identity import (
    AuthChallenge,
    PasswordCredential,
    Role,
    Session,
    User,
    UserContact,
    UserRole,
)
from app.models.privacy import ConsentPurpose, ConsentVersion, UserConsent
from app.security import hash_password

TEST_USERS = (
    ("emprendedora.prueba@kawsay.local", "EMPRENDEDORA"),
    ("administradora.prueba@kawsay.local", "ADMINISTRADORA"),
    ("curadora.rag.prueba@kawsay.local", "CURADORA_RAG"),
    ("auditora.prueba@kawsay.local", "AUDITORA_INVESTIGADORA"),
    ("servicio.interno.prueba@kawsay.local", "SERVICIO_INTERNO"),
)


def seed_test_users(password: str) -> None:
    settings = get_settings()
    if settings.app_env != "development":
        raise SystemExit("Las cuentas de prueba solo se pueden crear con APP_ENV=development")

    now = utc_now()
    password_hash = hash_password(password)

    with SessionLocal.begin() as db:
        roles = {
            role.code: role
            for role in db.scalars(
                select(Role).where(Role.code.in_(tuple(role for _, role in TEST_USERS)))
            )
        }
        missing_roles = sorted({role for _, role in TEST_USERS} - roles.keys())
        if missing_roles:
            raise SystemExit(f"Faltan roles iniciales: {', '.join(missing_roles)}")

        account_purpose = db.scalar(
            select(ConsentPurpose).where(ConsentPurpose.code == "ACCOUNT")
        )
        account_version = None
        if account_purpose is not None:
            account_version = db.scalar(
                select(ConsentVersion)
                .where(
                    ConsentVersion.purpose_id == account_purpose.id,
                    ConsentVersion.retired_at.is_(None),
                )
                .order_by(ConsentVersion.published_at.desc())
            )

        for email, role_code in TEST_USERS:
            contact = db.scalar(
                select(UserContact).where(
                    UserContact.contact_type == "EMAIL",
                    UserContact.value_normalized == email,
                )
            )
            if contact is None:
                user = User(status="ACTIVE")
                db.add(user)
                db.flush()
                contact = UserContact(
                    user_id=user.id,
                    contact_type="EMAIL",
                    value_normalized=email,
                    verified_at=now,
                    is_primary=True,
                )
                db.add(contact)
            else:
                user = db.get(User, contact.user_id)
                if user is None:
                    raise SystemExit(f"El contacto {email} no tiene una cuenta asociada")
                user.status = "ACTIVE"
                user.deleted_at = None
                contact.verified_at = now
                contact.is_primary = True

            credential = db.get(PasswordCredential, user.id)
            if credential is None:
                db.add(
                    PasswordCredential(
                        user_id=user.id,
                        password_hash=password_hash,
                        password_changed_at=now,
                    )
                )
            else:
                credential.password_hash = password_hash
                credential.password_changed_at = now
                credential.failed_attempts = 0
                credential.locked_until = None

            if db.get(UserPreference, user.id) is None:
                db.add(UserPreference(user_id=user.id))

            db.flush()
            db.execute(delete(Session).where(Session.user_id == user.id))
            db.execute(delete(AuthChallenge).where(AuthChallenge.contact_id == contact.id))
            db.execute(delete(UserRole).where(UserRole.user_id == user.id))
            db.add(UserRole(user_id=user.id, role_id=roles[role_code].id))

            if account_purpose is not None and account_version is not None:
                existing_consent = db.scalar(
                    select(UserConsent).where(
                        UserConsent.user_id == user.id,
                        UserConsent.purpose_id == account_purpose.id,
                        UserConsent.decision == "GRANTED",
                    )
                )
                if existing_consent is None:
                    evidence = f"{user.id}|ACCOUNT|GRANTED|TEST_SEED"
                    db.add(
                        UserConsent(
                            user_id=user.id,
                            purpose_id=account_purpose.id,
                            consent_version_id=account_version.id,
                            decision="GRANTED",
                            decided_at=now,
                            source="TEST_SEED",
                            evidence_hash=hashlib.sha256(evidence.encode()).hexdigest(),
                        )
                    )

    print("Cuentas de prueba listas:")
    for email, role_code in TEST_USERS:
        print(f"- {role_code}: {email}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--password",
        default=os.getenv("TEST_USER_PASSWORD"),
        help="Contraseña común (o variable TEST_USER_PASSWORD)",
    )
    args = parser.parse_args()
    if not args.password or len(args.password) < 12:
        raise SystemExit("Indique --password con al menos 12 caracteres")
    seed_test_users(args.password)


if __name__ == "__main__":
    main()
