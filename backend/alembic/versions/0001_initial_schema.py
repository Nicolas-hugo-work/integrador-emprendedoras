"""Esquema inicial para MariaDB 11.7.1+.

Revision ID: 0001_initial_schema
Revises: None
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

from app.models import Base


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


ROLE_SEEDS = [
    ("01990000-0000-7000-8000-000000000001", "EMPRENDEDORA", "Emprendedora"),
    ("01990000-0000-7000-8000-000000000002", "ADMINISTRADORA", "Administradora"),
    ("01990000-0000-7000-8000-000000000003", "CURADORA_RAG", "Curadora RAG"),
    ("01990000-0000-7000-8000-000000000004", "AUDITORA_INVESTIGADORA", "Auditora investigadora"),
    ("01990000-0000-7000-8000-000000000005", "SERVICIO_INTERNO", "Servicio interno"),
]

PERMISSION_SEEDS = [
    ("01990000-0000-7000-8100-000000000001", "profile.manage_own", "Administrar perfil propio"),
    ("01990000-0000-7000-8100-000000000002", "finance.read_own", "Leer finanzas propias"),
    ("01990000-0000-7000-8100-000000000003", "finance.write_own", "Registrar finanzas propias"),
    ("01990000-0000-7000-8100-000000000004", "conversation.manage_own", "Administrar conversaciones propias"),
    ("01990000-0000-7000-8100-000000000005", "source.review", "Revisar fuentes"),
    ("01990000-0000-7000-8100-000000000006", "source.publish", "Publicar o retirar fuentes"),
    ("01990000-0000-7000-8100-000000000007", "audit.read", "Consultar auditoría"),
    ("01990000-0000-7000-8100-000000000008", "account.suspend", "Suspender cuentas"),
    ("01990000-0000-7000-8100-000000000009", "research.read_anonymized", "Consultar investigación anonimizada"),
    ("01990000-0000-7000-8100-000000000010", "jobs.execute", "Ejecutar trabajos internos"),
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    seeded_at = datetime.now(timezone.utc).replace(tzinfo=None)

    op.execute(
        "CREATE FULLTEXT INDEX idx_source_chunks_fulltext "
        "ON source_chunks (heading, content)"
    )
    op.execute(
        "CREATE VECTOR INDEX idx_chunk_embedding ON source_chunk_embeddings (embedding) "
        "M=8 DISTANCE=cosine"
    )
    op.execute(
        """
        CREATE VIEW v_monthly_financial_summary AS
        SELECT
            user_id,
            business_id,
            CAST(DATE_FORMAT(occurred_on, '%Y-%m-01') AS DATE) AS period_start,
            currency,
            SUM(CASE WHEN movement_type = 'INCOME' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN movement_type IN ('EXPENSE','COST') THEN amount ELSE 0 END) AS total_outflow,
            SUM(CASE WHEN movement_type = 'INCOME' THEN amount
                     WHEN movement_type IN ('EXPENSE','COST') THEN -amount
                     ELSE 0 END) AS balance
        FROM financial_movements
        WHERE deleted_at IS NULL
        GROUP BY user_id, business_id, period_start, currency
        """
    )
    op.execute(
        "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
        "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit_events is append-only'"
    )
    op.execute(
        "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
        "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit_events is append-only'"
    )

    roles = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": role_id,
                "code": code,
                "name": name,
                "description": name,
                "is_system": True,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            }
            for role_id, code, name in ROLE_SEEDS
        ],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": permission_id,
                "code": code,
                "description": description,
                "created_at": seeded_at,
                "updated_at": seeded_at,
            }
            for permission_id, code, description in PERMISSION_SEEDS
        ],
    )

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )
    grants = {
        ROLE_SEEDS[0][0]: [0, 1, 2, 3],
        ROLE_SEEDS[1][0]: [6, 7],
        ROLE_SEEDS[2][0]: [4, 5],
        ROLE_SEEDS[3][0]: [6, 8],
        ROLE_SEEDS[4][0]: [9],
    }
    op.bulk_insert(
        role_permissions,
        [
            {"role_id": role_id, "permission_id": PERMISSION_SEEDS[index][0]}
            for role_id, indexes in grants.items()
            for index in indexes
        ],
    )

    op.execute(
        """
        INSERT INTO consent_purposes
            (id, code, name, is_required, withdrawal_effect, created_at, updated_at)
        VALUES
            ('01990000-0000-7000-8200-000000000001','ACCOUNT','Cuenta',1,
             'El retiro inicia el cierre y eliminación de la cuenta',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8200-000000000002','AUDIO','Audio',0,
             'Desactiva grabación y elimina audios temporales',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8200-000000000003','RESEARCH','Investigación',0,
             'Excluye nuevos usos de investigación',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8200-000000000004','SECONDARY_USE','Uso secundario',0,
             'Impide reutilizar datos para fines secundarios',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))
        """
    )
    op.execute(
        """
        INSERT INTO consent_versions
            (id, purpose_id, version, notice_text, notice_hash, published_at, created_at, updated_at)
        VALUES
            ('01990000-0000-7000-8210-000000000001','01990000-0000-7000-8200-000000000001','1.0',
             'Autorizo la creación y gestión de mi cuenta.','b02804e3beecd2025d487a0b6592b9514f2911f690e7cfa0fc1e5b7128cbf079',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8210-000000000002','01990000-0000-7000-8200-000000000002','1.0',
             'Autorizo el procesamiento temporal de audio.','2a7fb5dc1e25cfb392589c90477903273014663b9d1969d9a93e51bb26ce9472',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8210-000000000003','01990000-0000-7000-8200-000000000003','1.0',
             'Autorizo el uso seudonimizado de datos para el piloto académico.','f8ab16f9e8b10e7af846bdcecfb23535e7efb9136bb8870be2ea9bf99fff866a',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8210-000000000004','01990000-0000-7000-8200-000000000004','1.0',
             'Autorizo usos secundarios descritos de forma separada.','99b97aa10658b1f0b1bfbe60f3cf5296a5c71bbc0350ad4b51805ce92ce31edc',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))
        """
    )
    op.execute(
        """
        INSERT INTO financial_categories
            (id, code, name, movement_type, is_system, created_at, updated_at)
        VALUES
            ('01990000-0000-7000-8300-000000000001','SALES','Ventas','INCOME',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8300-000000000002','OTHER_INCOME','Otros ingresos','INCOME',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8300-000000000003','SUPPLIES','Insumos','COST',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8300-000000000004','SERVICES','Servicios','EXPENSE',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8300-000000000005','TRANSFER','Transferencia hogar-negocio','TRANSFER',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))
        """
    )
    op.execute(
        """
        INSERT INTO embedding_models
            (id, code, provider, model_name, model_version, dimension, distance_metric,
             is_active, created_at, updated_at)
        VALUES
            ('01990000-0000-7000-8400-000000000001','multilingual-768-v1','CONFIGURABLE',
             'multilingual-embedding','v1',768,'COSINE',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))
        """
    )
    op.execute(
        """
        INSERT INTO source_publishers
            (id, code, name, official_domain, country_code, created_at, updated_at)
        VALUES
            ('01990000-0000-7000-8500-000000000001','SEPREC','Servicio Plurinacional de Registro de Comercio','seprec.gob.bo','BO',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8500-000000000002','SIN','Servicio de Impuestos Nacionales','impuestos.gob.bo','BO',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8500-000000000003','INE','Instituto Nacional de Estadística','ine.gob.bo','BO',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
            ('01990000-0000-7000-8500-000000000004','GACETA','Gaceta Oficial de Bolivia','gacetaoficialdebolivia.gob.bo','BO',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update")
    op.execute("DROP VIEW IF EXISTS v_monthly_financial_summary")
    Base.metadata.drop_all(bind=op.get_bind())
