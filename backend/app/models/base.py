from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, MetaData
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.dialects.mysql import base as mysql_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UserDefinedType
from uuid6 import uuid7

from app.core.clock import utc_now

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
    """Columna `VECTOR(768)` de MariaDB 11.7+.

    Acepta la dimensión como argumento posicional porque el reflector del
    dialecto MySQL construye el tipo con los argumentos que lee del DDL: al
    reflejar `VECTOR(768)` llama a `Vector768(768)`.
    """

    cache_ok = True

    def __init__(self, dimension: int = 768, **kw: Any) -> None:
        super().__init__()
        self.dimension = int(dimension)

    def get_col_spec(self, **kw: Any) -> str:
        return f"VECTOR({self.dimension})"


# Sin este registro, reflejar `source_chunk_embeddings` falla con
# `TypeError: NullType() takes no arguments`, porque el dialecto no conoce el
# tipo `VECTOR` y termina construyendo `NullType(768)`. Eso dejaba inservibles
# `alembic check` y `alembic revision --autogenerate` sobre este esquema.
mysql_base.ischema_names["vector"] = Vector768


class DateTime6(DATETIME):
    """DATETIME(6) sin zona; todos los valores se normalizan a UTC en la aplicación."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fsp", 6)
        super().__init__(*args, **kwargs)


def new_uuid7() -> str:
    return str(uuid7())


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
