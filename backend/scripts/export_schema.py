"""Exporta un schema.sql autocontenido usando el dialecto MariaDB de SQLAlchemy."""

from pathlib import Path

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sql" / "schema.sql"

EXTRAS = """
CREATE FULLTEXT INDEX idx_source_chunks_fulltext
    ON source_chunks (heading, content);

CREATE VECTOR INDEX idx_chunk_embedding
    ON source_chunk_embeddings (embedding) M=8 DISTANCE=cosine;

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
GROUP BY user_id, business_id, period_start, currency;

CREATE TRIGGER trg_audit_events_no_update
BEFORE UPDATE ON audit_events
FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit_events is append-only';

CREATE TRIGGER trg_audit_events_no_delete
BEFORE DELETE ON audit_events
FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit_events is append-only';
""".strip()


def build_sql() -> str:
    dialect = mysql.dialect()
    statements = [
        "-- Generado desde app.models. Requiere MariaDB 11.7.1+.",
        "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "SET time_zone = '+00:00';",
    ]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    statements.append(EXTRAS)
    statements.append((ROOT / "sql" / "seeds.sql").read_text(encoding="utf-8").strip())
    return "\n\n".join(statements) + "\n"


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_sql(), encoding="utf-8")
    print(OUTPUT)

