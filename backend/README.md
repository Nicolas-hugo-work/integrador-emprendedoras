# Backend y base de datos — Kawsay

Backend funcional del MVP para MariaDB 11.8 LTS. Incluye 62 tablas, RBAC, consentimiento versionado, libro financiero simple, conversaciones cifradas, trazabilidad RAG, búsqueda vectorial, auditoría inmutable y datos seudonimizados del piloto.

## Contenido

- Modelos SQLAlchemy organizados por dominio en `app/models/`.
- Contratos Pydantic y esqueleto OpenAPI en `app/api_contracts.py` y `app/main.py`.
- Migración Alembic inicial reversible en `alembic/versions/0001_initial_schema.py`.
- Índices `BTREE`, `FULLTEXT` y `VECTOR(768)` con distancia coseno.
- Vista mensual financiera y protección append-only de auditoría.
- Semillas idempotentes para roles, permisos, consentimientos, categorías y embeddings.
- Diagrama ER y diccionario resumido en `docs/architecture.md`.
- Pruebas de reglas financieras, privacidad, evidencia RAG y cobertura estructural.

## Inicio rápido

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\uvicorn.exe app.main:app --reload
```

La documentación OpenAPI quedará disponible en `http://127.0.0.1:8000/docs`.

## SQL autocontenido

La migración Alembic es la fuente autoritativa. Para exportar el mismo esquema como `sql/schema.sql`:

```powershell
.venv\Scripts\python.exe scripts\export_schema.py
```

El archivo generado incluye tablas, restricciones, índices convencionales, índice `FULLTEXT`, índice vectorial, vista, triggers y semillas.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\ruff.exe check .
```

Para validar contra MariaDB real, ejecutar primero `docker compose up -d` y luego la migración ascendente y descendente en una base de prueba independiente.

## Estado de los endpoints

Están operativos el registro y verificación, sesiones JWT, emprendimientos, categorías y movimientos financieros, costos, escenarios de precios, resumen, conversaciones, consulta segura RAG, retroalimentación, consentimientos, exportación, eliminación de cuenta y curaduría de fuentes protegida mediante RBAC.

## Decisiones de seguridad

- Contraseñas: Argon2id.
- Tokens de sesión y verificación: solo hash en base de datos.
- Texto sensible: columnas `*_encrypted`; la clave permanece fuera de MariaDB.
- Audio y documentos: almacenamiento de objetos; la base conserva únicamente `storage_key`.
- Audio: purga al confirmar la transcripción o al llegar a 24 horas.
- Cuenta eliminada: purga física en 30 días.
- Auditoría: 12 meses, seudonimizada y sin contenido privado.
- Alertas de seguridad: 90 días.
- Conversaciones privadas: excluidas de entrenamiento y RAG por defecto.
