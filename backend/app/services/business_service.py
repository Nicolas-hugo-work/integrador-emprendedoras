"""Emprendimientos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessMembership
from app.models.identity import User
from app.services.audit_service import write_audit


def create_business(db: Session, user: User, payload) -> Business:
    """Crea un emprendimiento y da de alta a la propietaria como miembro."""
    # Campos explícitos en lugar de `**payload.model_dump()`: así un campo nuevo
    # en el contrato no se escribe solo en el modelo persistente.
    business = Business(
        owner_user_id=user.id,
        name=payload.name,
        stage=payload.stage,
        activity=payload.activity,
        department_code=payload.department_code,
        municipality=payload.municipality,
    )
    db.add(business)
    db.flush()
    db.add(BusinessMembership(business_id=business.id, user_id=user.id, member_role="OWNER"))
    write_audit(db, actor=user, action="business.create", object_type="business", object_id=business.id)
    db.commit()
    db.refresh(business)
    return business


def list_businesses(db: Session, user: User) -> list[Business]:
    """Lista los emprendimientos vigentes de la usuaria."""
    return list(
        db.scalars(
            select(Business)
            .where(Business.owner_user_id == user.id, Business.deleted_at.is_(None))
            .order_by(Business.created_at.desc())
        )
    )
