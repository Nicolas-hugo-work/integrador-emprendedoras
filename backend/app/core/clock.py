"""Reloj único del backend.

`datetime.utcnow()` está obsoleto desde Python 3.12 y convivía con
`datetime.now(UTC)` en `security.py`, mezclando fechas naive y aware.

Las columnas `DATETIME` de MariaDB son naive y todo el esquema guarda UTC, así
que `utc_now()` devuelve un instante UTC sin `tzinfo`: mismo valor que producía
`datetime.utcnow()` en `v0.1.0`, sin la llamada obsoleta.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Instante actual en UTC, sin `tzinfo`, para columnas `DATETIME`."""
    return datetime.now(UTC).replace(tzinfo=None)


def utc_now_aware() -> datetime:
    """Instante actual en UTC con `tzinfo`, para JWT y comparaciones aware."""
    return datetime.now(UTC)
