# Contratos API y autorización

Los modelos Pydantic de `app/api_contracts.py` son la fuente de verdad inicial para OpenAPI.

| Área | Rutas | Permiso mínimo |
|---|---|---|
| Sistema | `/health` | Público |
| Cuenta | `/auth/*`, `/me` | Sesión propia (salvo registro, login y verify) |
| Privacidad | `/consents`, `/privacy/export`, `/privacy/deletion` | Propietaria del dato |
| Emprendimiento | `/businesses` | `business.manage_own` |
| Finanzas | `/finance/movements`, `/finance/costs`, `/finance/pricing`, `/finance/summary` | `finance.read_own` o `finance.write_own` |
| Asistente | `/conversations`, `/assistant/query`, `/feedback` | `conversation.manage_own` |
| RAG | `/sources`, `/source-versions`, `/source-chunks`, `/source-publishers` | `source.review` o `source.publish` |
| Administración | `/accounts`, `/security-alerts` | `account.suspend` o `audit.read` |
| Auditoría | `/audit-events` | `audit.read` |
| Evaluación | `/evaluation/sets`, `/evaluation/runs` | escribir: `source.review`; leer: `source.review` o `audit.read` |

No hay HTTP para `/diagnostics`, `/formalization-routes`, organizaciones ni `business_memberships`. Esas tablas son reserva de esquema.

Toda consulta con un recurso perteneciente a una usuaria debe filtrar simultáneamente por `resource.id` y `user_id`. No se autoriza primero y consulta después: la propiedad forma parte de la propia consulta SQL para evitar acceso horizontal.

`POST /assistant/query` devuelve siempre `trace_id`. Una respuesta normativa debe contener citas vigentes y advertencia; cuando no exista evidencia pertinente, `abstained=true`, sin contenido normativo improvisado.
