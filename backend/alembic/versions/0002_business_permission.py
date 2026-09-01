"""Permiso business.manage_own para la gestión de emprendimientos.

Revision ID: 0002_business_permission
Revises: 0001_initial_schema

El catálogo sembrado en `0001` tiene permisos para finanzas, conversaciones y
perfil, pero ninguno para `/businesses`. Sin él, v0.4.0 no puede exigir permiso
en los endpoints de emprendimientos sin dejar fuera a todas las usuarias.

Es una migración **de datos**: no crea ni altera tablas, así que la huella de
`information_schema` queda idéntica.
"""

from alembic import op

revision = "0002_business_permission"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

#: Continúa la serie sembrada en `0001`, que llega hasta ...0010.
PERMISSION_ID = "01990000-0000-7000-8100-000000000011"
PERMISSION_CODE = "business.manage_own"

#: `EMPRENDEDORA`, sembrado en `0001`.
EMPRENDEDORA_ROLE_ID = "01990000-0000-7000-8000-000000000001"


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (id, code, description, created_at, updated_at) "
        f"VALUES ('{PERMISSION_ID}', '{PERMISSION_CODE}', "
        "'Administrar emprendimientos propios', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
    )
    # La concesión debe existir antes de que los endpoints empiecen a exigir el
    # permiso: de lo contrario toda cuenta ya registrada pierde acceso a sus
    # propios emprendimientos.
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        f"VALUES ('{EMPRENDEDORA_ROLE_ID}', '{PERMISSION_ID}')"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM role_permissions WHERE permission_id = '{PERMISSION_ID}'")
    op.execute(f"DELETE FROM permissions WHERE id = '{PERMISSION_ID}'")
