# Contratos API y autorización

Los modelos Pydantic de `app/api_contracts.py` son la fuente de verdad inicial para OpenAPI.

| Área | Rutas previstas | Permiso mínimo |
|---|---|---|
| Cuenta | `/auth`, `/me` | Sesión propia |
| Privacidad | `/consents`, `/privacy/export`, `/privacy/deletion` | Propietaria del dato |
| Emprendimiento | `/businesses`, `/diagnostics`, `/formalization-routes` | `profile.manage_own` |
| Finanzas | `/finance/movements`, `/finance/costs`, `/finance/pricing`, `/finance/summary` | `finance.read_own` o `finance.write_own` |
| Asistente | `/conversations`, `/messages`, `/assistant/query`, `/feedback` | `conversation.manage_own` |
| RAG | `/sources`, `/source-versions`, `/ingestion-jobs` | `source.review` o `source.publish` |
| Administración | `/admin/accounts`, `/admin/alerts`, `/admin/audit` | `account.suspend` o `audit.read` |
| Evaluación | `/evaluations`, `/research` | `research.read_anonymized` |

Toda consulta con un recurso perteneciente a una usuaria debe filtrar simultáneamente por `resource.id` y `user_id`. No se autoriza primero y consulta después: la propiedad forma parte de la propia consulta SQL para evitar acceso horizontal.

`POST /assistant/query` devuelve siempre `trace_id`. Una respuesta normativa debe contener citas vigentes y advertencia; cuando no exista evidencia pertinente, `abstained=true`, sin contenido normativo improvisado.

