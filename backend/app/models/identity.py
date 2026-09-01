from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.base import DateTime6 as DateTime


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','ACTIVE','SUSPENDED','DELETED')", name="valid_status"
        ),
        Index("ix_users_status_deleted", "status", "deleted_at"),
    )

    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    locale: Mapped[str] = mapped_column(String(12), default="es-BO", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/La_Paz", nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime())


class UserContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_contacts"
    __table_args__ = (
        UniqueConstraint("contact_type", "value_normalized", name="uq_contact_type_value"),
        CheckConstraint("contact_type IN ('EMAIL','PHONE')", name="valid_type"),
        Index("ix_user_contacts_user_primary", "user_id", "is_primary"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    contact_type: Mapped[str] = mapped_column(String(8), nullable=False)
    value_normalized: Mapped[str] = mapped_column(String(254), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime())
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PasswordCredential(TimestampMixin, Base):
    __tablename__ = "password_credentials"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime())


class AuthChallenge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_challenges"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('VERIFY_CONTACT','RESET_PASSWORD')", name="valid_purpose"
        ),
        Index("ix_auth_challenges_contact_expiry", "contact_id", "expires_at", "consumed_at"),
    )

    contact_id: Mapped[str] = mapped_column(
        ForeignKey("user_contacts.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime())
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_expiry", "user_id", "expires_at", "revoked_at"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    device_label: Mapped[str | None] = mapped_column(String(120))
    user_agent_hash: Mapped[str | None] = mapped_column(String(128))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime())


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(TimestampMixin, Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    assigned_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="valid_status"),
    )

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        CheckConstraint("member_role IN ('OWNER','MEMBER','VIEWER')", name="valid_role"),
    )

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    member_role: Mapped[str] = mapped_column(String(16), nullable=False)
