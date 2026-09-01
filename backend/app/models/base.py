from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CHAR, MetaData
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UserDefinedType
from uuid6 import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Vector768(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "VECTOR(768)"


class DateTime6(DATETIME):
    """DATETIME(6) sin zona; todos los valores se normalizan a UTC en la aplicación."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fsp", 6)
        super().__init__(*args, **kwargs)


def new_uuid7() -> str:
    return str(uuid7())


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime6(), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime6(), default=utc_now, onupdate=utc_now, nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime6())
