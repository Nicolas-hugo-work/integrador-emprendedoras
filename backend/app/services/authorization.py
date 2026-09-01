"""Autorización: permisos RBAC y propiedad de recursos."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import Forbidden, NotFound
from app.models.business import Business
from app.models.identity import Permission, RolePermission, User, UserRole


def assert_permission(db: Session, user: User, permission_code: str) -> None:
    """Exige que la usuaria tenga el permiso indicado a través de algún rol."""
    allowed = db.scalar(
        select(func.count())
        .select_from(UserRole)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == user.id, Permission.code == permission_code)
    )
    if not allowed:
        raise Forbidden("Permiso insuficiente")


def owned_business(db: Session, user: User, business_id: str) -> Business:
    """Devuelve el emprendimiento solo si pertenece a la usuaria.

    Un emprendimiento ajeno produce el mismo `NotFound` que uno inexistente:
    la respuesta no debe permitir descubrir la existencia de datos de terceras.
    """
    business = db.scalar(
        select(Business).where(
            Business.id == business_id,
            Business.owner_user_id == user.id,
            Business.deleted_at.is_(None),
        )
    )
    if business is None:
        raise NotFound("Emprendimiento no encontrado")
    return business
