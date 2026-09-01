"""Cuenta de la usuaria autenticada."""

from sqlalchemy.orm import Session

from app.api_contracts import UserView
from app.models.identity import User
from app.services.authorization import roles_and_permissions


def current_account(db: Session, user: User) -> UserView:
    """Perfil de la usuaria junto con sus roles y permisos vigentes.

    Los permisos viajan al cliente para que la interfaz se condicione por
    capacidad —los mismos códigos que exige `assert_permission`— en lugar de
    codificar «si el rol es X entonces...», que se desalinea en cuanto cambian
    las concesiones de un rol.
    """
    roles, permissions = roles_and_permissions(db, user)
    return UserView(
        id=user.id,
        status=user.status,
        locale=user.locale,
        timezone=user.timezone,
        roles=roles,
        permissions=permissions,
    )
