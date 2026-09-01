"""Asigna un rol local a una cuenta ya registrada."""

import argparse
import re

from sqlalchemy import select

from app.database import SessionLocal
from app.models.identity import Role, UserContact, UserRole


def normalize(value: str) -> str:
    return value.casefold().strip() if "@" in value else re.sub(r"[^0-9+]", "", value)


def assign(contact_value: str, role_code: str) -> None:
    with SessionLocal.begin() as db:
        contact = db.scalar(
            select(UserContact).where(UserContact.value_normalized == normalize(contact_value))
        )
        role = db.scalar(select(Role).where(Role.code == role_code))
        if contact is None:
            raise SystemExit("No existe una cuenta con ese contacto")
        if role is None:
            raise SystemExit(f"El rol {role_code} no existe")
        current = db.get(UserRole, (contact.user_id, role.id))
        if current is None:
            db.add(UserRole(user_id=contact.user_id, role_id=role.id))
    print(f"Rol {role_code} asignado a {contact_value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("contact")
    parser.add_argument("role", choices=["ADMINISTRADORA", "CURADORA_RAG", "AUDITORA_INVESTIGADORA"])
    args = parser.parse_args()
    assign(args.contact, args.role)
