"""Cuenta de la usuaria autenticada."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api_contracts import AccountView, UserView
from app.core.clock import utc_now
from app.core.exceptions import Conflict, NotFound
from app.models.identity import Session as AuthSession
from app.models.identity import User, UserContact
from app.services.audit_service import write_audit
from app.services.auth_service import normalize_contact_for_lookup
from app.services.authorization import assert_permission, roles_and_permissions


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


def _view(db: Session, target: User) -> AccountView:
    roles, _ = roles_and_permissions(db, target)
    return AccountView(
        id=target.id, status=target.status, roles=roles, created_at=target.created_at
    )


def lookup_account(db: Session, user: User, contact: str) -> AccountView:
    """Busca una cuenta por su contacto **completo**.

    No admite comodines ni listados: exige el correo o teléfono exacto, de modo
    que sirve para actuar sobre un caso reportado pero no para explorar el
    padrón de usuarias. Cada búsqueda deja evento de auditoría con quién buscó.
    """
    assert_permission(db, user, "account.suspend")
    normalizado = normalize_contact_for_lookup(contact)
    encontrado = db.scalar(
        select(UserContact).where(UserContact.value_normalized == normalizado)
    )
    target = db.get(User, encontrado.user_id) if encontrado else None
    if target is None:
        raise NotFound("Cuenta no encontrada")

    write_audit(
        db, actor=user, action="account.lookup", object_type="user", object_id=target.id
    )
    db.commit()
    return _view(db, target)


def read_account(db: Session, user: User, target_id: str) -> AccountView:
    """Ficha de una cuenta por su identificador.

    Es lo que permite ir desde una alerta —que sí lleva `user_id`— hasta el
    estado y los roles de la cuenta antes de decidir si se suspende. Queda
    auditada igual que la búsqueda por contacto.
    """
    assert_permission(db, user, "account.suspend")
    target = db.get(User, target_id)
    if target is None:
        raise NotFound("Cuenta no encontrada")
    write_audit(
        db, actor=user, action="account.read", object_type="user", object_id=target.id
    )
    db.commit()
    return _view(db, target)


def _target_for_admin_action(db: Session, user: User, target_id: str) -> User:
    assert_permission(db, user, "account.suspend")
    if target_id == user.id:
        raise Conflict("No puede suspender ni reactivar su propia cuenta")
    target = db.get(User, target_id)
    if target is None:
        raise NotFound("Cuenta no encontrada")
    return target


def suspend_account(db: Session, user: User, target_id: str, payload) -> AccountView:
    """Suspende una cuenta y revoca todas sus sesiones.

    `get_current_user` ya rechaza cualquier estado distinto de `ACTIVE`, así que
    el token de acceso vigente deja de servir de inmediato; sin sesiones no hay
    renovación posible.
    """
    target = _target_for_admin_action(db, user, target_id)
    _, permisos = roles_and_permissions(db, target)
    if "account.suspend" in permisos:
        # Si el personal de administración pudiera suspenderse entre sí, sería
        # posible dejar el sistema sin nadie que lo administre.
        raise Conflict("No puede suspender a otra cuenta de administración")
    if target.status == "DELETED":
        raise Conflict("La cuenta está eliminada")
    if target.status == "SUSPENDED":
        raise Conflict("La cuenta ya está suspendida")

    target.status = "SUSPENDED"
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )
    write_audit(
        db,
        actor=user,
        action="account.suspend",
        object_type="user",
        object_id=target.id,
        metadata={"reason": payload.reason},
    )
    db.commit()
    return _view(db, target)


def reactivate_account(db: Session, user: User, target_id: str) -> AccountView:
    """Devuelve el acceso a una cuenta suspendida.

    Solo desde `SUSPENDED`: una cuenta eliminada no vuelve por esta vía, porque
    su purga ya está programada y revivirla contradiría lo que se le prometió.
    """
    target = _target_for_admin_action(db, user, target_id)
    if target.status != "SUSPENDED":
        raise Conflict("Solo se puede reactivar una cuenta suspendida")

    target.status = "ACTIVE"
    write_audit(
        db, actor=user, action="account.reactivate", object_type="user", object_id=target.id
    )
    db.commit()
    return _view(db, target)
