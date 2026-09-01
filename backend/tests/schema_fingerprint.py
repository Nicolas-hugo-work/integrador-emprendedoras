"""Huella del esquema real de MariaDB.

Reemplaza al criterio "conservar el checksum de `0001_initial_schema.py`", que
no detectaba nada: esa migración ejecuta `Base.metadata.create_all()`, así que
el esquema proviene de `app/models/` y el archivo puede quedar idéntico
mientras las tablas cambian por completo.

Esta huella lee `information_schema` después de migrar y describe tablas,
columnas, índices, restricciones, vistas y triggers. Compararla antes y después
del refactor sí detecta una regresión de esquema.
"""

from typing import Any

from sqlalchemy import Engine, text

_COLUMNS = text(
    """
    SELECT table_name, column_name, column_type, is_nullable, column_default, extra
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
    ORDER BY table_name, column_name
    """
)

_TABLES = text(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
)

_INDEXES = text(
    """
    SELECT table_name, index_name, non_unique, index_type,
           GROUP_CONCAT(column_name ORDER BY seq_in_index) AS columns
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
    GROUP BY table_name, index_name, non_unique, index_type
    ORDER BY table_name, index_name
    """
)

_CONSTRAINTS = text(
    """
    SELECT table_name, constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
    ORDER BY table_name, constraint_name
    """
)

_FOREIGN_KEYS = text(
    """
    SELECT table_name, constraint_name, column_name,
           referenced_table_name, referenced_column_name
    FROM information_schema.key_column_usage
    WHERE table_schema = DATABASE() AND referenced_table_name IS NOT NULL
    ORDER BY table_name, constraint_name, ordinal_position
    """
)

_VIEWS = text(
    """
    SELECT table_name
    FROM information_schema.views
    WHERE table_schema = DATABASE()
    ORDER BY table_name
    """
)

_TRIGGERS = text(
    """
    SELECT trigger_name, event_manipulation, event_object_table, action_timing
    FROM information_schema.triggers
    WHERE trigger_schema = DATABASE()
    ORDER BY trigger_name
    """
)


#: Tabla de control de Alembic: no forma parte del esquema de la aplicación y
#: por eso queda fuera de la huella y del recuento de 62 tablas.
BOOKKEEPING_TABLES = frozenset({"alembic_version"})


def build_fingerprint(engine: Engine) -> dict[str, Any]:
    """Devuelve una descripción comparable y estable del esquema vigente."""
    with engine.connect() as connection:
        tables = [row[0] for row in connection.execute(_TABLES) if row[0] not in BOOKKEEPING_TABLES]

        columns: dict[str, list[str]] = {}
        for table, column, column_type, nullable, default, extra in connection.execute(_COLUMNS):
            if table in BOOKKEEPING_TABLES:
                continue
            columns.setdefault(table, []).append(
                f"{column} {column_type} "
                f"{'NULL' if nullable == 'YES' else 'NOT NULL'} "
                f"default={default!r} extra={extra!r}"
            )

        indexes: dict[str, list[str]] = {}
        for table, name, non_unique, index_type, cols in connection.execute(_INDEXES):
            if table in BOOKKEEPING_TABLES:
                continue
            indexes.setdefault(table, []).append(
                f"{name} ({cols}) unique={not non_unique} type={index_type}"
            )

        constraints: dict[str, list[str]] = {}
        for table, name, kind in connection.execute(_CONSTRAINTS):
            if table in BOOKKEEPING_TABLES:
                continue
            constraints.setdefault(table, []).append(f"{name} {kind}")

        foreign_keys: dict[str, list[str]] = {}
        for table, name, column, ref_table, ref_column in connection.execute(_FOREIGN_KEYS):
            foreign_keys.setdefault(table, []).append(
                f"{name}: {column} -> {ref_table}.{ref_column}"
            )

        views = [row[0] for row in connection.execute(_VIEWS)]
        triggers = [
            f"{name} {timing} {event} ON {table}"
            for name, event, table, timing in connection.execute(_TRIGGERS)
        ]

    return {
        "table_count": len(tables),
        "tables": tables,
        "columns": {table: sorted(values) for table, values in sorted(columns.items())},
        "indexes": {table: sorted(values) for table, values in sorted(indexes.items())},
        "constraints": {table: sorted(values) for table, values in sorted(constraints.items())},
        "foreign_keys": {table: sorted(values) for table, values in sorted(foreign_keys.items())},
        "views": views,
        "triggers": sorted(triggers),
    }
