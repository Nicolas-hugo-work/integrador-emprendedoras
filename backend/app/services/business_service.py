"""Emprendimientos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.models.business import Business, BusinessMembership
from app.models.identity import User
from app.services.audit_service import write_audit
from app.services.authorization import owned_business


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


def update_business(db: Session, user: User, business_id: str, payload) -> Business:
    """Corrige los datos del emprendimiento. Solo escribe lo que viene."""
    business = owned_business(db, user, business_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    write_audit(
        db, actor=user, action="business.update", object_type="business", object_id=business.id
    )
    db.commit()
    db.refresh(business)
    return business


def delete_business(db: Session, user: User, business_id: str) -> None:
    """Borrado lógico del emprendimiento.

    No se toca el historial financiero: los movimientos conservan su
    `business_id` y siguen en el listado general. Como `owned_business` filtra
    por `deleted_at`, cualquier operación posterior sobre este negocio responde
    404.
    """
    business = owned_business(db, user, business_id)
    business.deleted_at = utc_now()
    write_audit(
        db, actor=user, action="business.delete", object_type="business", object_id=business.id
    )
    db.commit()
