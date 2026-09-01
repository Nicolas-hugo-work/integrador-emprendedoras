# Informe de implementación — Kawsay v0.2.0

**Rama:** `refactor/v0.2.0` · **Pull request:** [#1](https://github.com/Nicolas-hugo-work/integrador-emprendedoras/pull/1)
**Base:** `main` (`3ec2663`, etiqueta `v0.1.0`) · **Fecha:** 2026-09-01

Implementación completa del plan acordado en `PLAN_REFACTOR_MVC_v0.2.0.md`.
Las cinco fases quedaron terminadas. El pull request **no se fusionó** y no se
reescribió historial remoto.

---

## 1. Funcionalidades implementadas

### Fase A — Red de seguridad

- **Integración continua** (`.github/workflows/ci.yml`), inexistente hasta
  ahora. Tres trabajos: backend con MariaDB 11.8 real, frontend
  (oxlint + tsc + Vitest + build) y arranque de Docker Compose desde cero.
  Define `TEST_DATABASE_URL` y `TEST_MIGRATION_DATABASE_URL`, y **falla si
  alguna prueba de integración queda omitida**: hasta ahora la única prueba
  que tocaba la base se saltaba siempre en silencio.
- **Snapshot de OpenAPI** (`backend/tests/contracts/openapi_v0_1.json`) con las
  26 operaciones de `v0.1.0`, más la prueba que lo compara.
- **Huella de esquema** (`backend/tests/contracts/schema_v0_1.json`): 62 tablas,
  537 columnas, 169 índices, 78 claves foráneas, 1 vista y 2 triggers leídos de
  `information_schema`. Sustituye al criterio del checksum de la migración.
- **Pruebas de reglas de capas** sobre el árbol de sintaxis.

### Fase B — Refactor

- `backend/app/main.py`: de **733 a 49 líneas**. Solo crea la aplicación,
  configura CORS, traduce errores y registra routers. Se conserva
  `app = create_app()` para no romper `uvicorn app.main:app` ni Docker.
- **8 routers** en `backend/app/routers/`: solo protocolo HTTP.
- **8 servicios** en `backend/app/services/`: casos de uso, dueños del `commit`.
- `backend/app/core/exceptions.py`: excepciones independientes de FastAPI,
  traducidas por un único manejador conservando los textos de `detail`.
- `backend/app/core/clock.py`: un solo `utc_now()`.
- `assistant_query` (94 líneas) descompuesto **dentro** de
  `assistant_service.py`, no repartido en varios archivos.
- **Sin capa de repositorios**, conforme al plan revisado.

### Fase C — Correcciones

1. Guardián de secretos: la aplicación no arranca con `APP_ENV` distinto de
   `development` si `JWT_SECRET` o `CONTENT_ENCRYPTION_KEY` conservan el valor
   de ejemplo o miden menos de 32 caracteres.
2. `/auth/register` deja de permitir enumerar cuentas.
3. Límite de intentos en `/auth/login` (por contacto y por dirección) y en
   `/auth/verify-contact`, con retroceso que se duplica.
4. Colisión de `sequence_number`: `SELECT … FOR UPDATE` sobre la conversación
   más un reintento ante `IntegrityError`.
5. `utc_now()` unificado; se elimina `datetime.utcnow()`.
6. Regla de transferencia con un solo hogar: `FinancialMovementCreate` delega en
   `domain_rules.validate_transfer`.
7. `financial_summary` usa `movement_balance_effect`.
8. `create_business` con campos explícitos en vez de `**model_dump()`.
9. `write_audit` valida el resultado contra `ck_audit_events_valid_result`.

### Fase D — Frontend

- `app/lib/api.ts`: renovación transparente del token ante un `401`, con una
  sola renovación compartida entre peticiones simultáneas. El `refresh_token`
  se guardaba desde `v0.1.0` pero no se usaba nunca.
- `app/types/api.ts`: contratos compartidos, antes redeclarados en cuatro
  páginas.
- `app/lib/form.ts`: lectura segura de `FormData`.
- `npm run lint` pasa a ser real (`oxlint && tsc --noEmit`); se instalan
  `oxlint`, `oxfmt` y `oxlint-tsgolint`, cuyas configuraciones ya existían sin
  las herramientas.
- Vitest con 10 casos sobre el cliente HTTP.
- Código propio reformateado con `oxfmt`.

### Fase E — Cierre

- `VERSION`, `backend/pyproject.toml`, `frontend/package.json` y FastAPI
  sincronizados en `0.2.0`.
- `CHANGELOG.md` con los cambios de comportamiento aprobados.

---

## 2. Archivos principales

**Nuevos (backend):** `app/core/{exceptions,clock}.py`; `app/routers/` (8
routers); `app/services/` (8 servicios más `rate_limit.py`);
`tests/{conftest,schema_fingerprint}.py`; `tests/contracts/` (2 snapshots);
`tests/test_{contracts,architecture,http_smoke,horizontal_access,rag,privacy,auth_hardening}.py`.

**Modificados (backend):** `app/main.py` (733 → 49 líneas), `app/config.py`,
`app/domain_rules.py`, `app/api_contracts.py`, `app/tasks.py`,
`app/models/base.py`, `.env.example`, `tests/test_{mariadb_integration,schema_static}.py`.

**Nuevos (frontend):** `app/types/api.ts`, `app/lib/form.ts`,
`tests/api.test.ts`, `vitest.config.mts`.

**Modificados (frontend):** `app/lib/api.ts`, las 6 páginas, `package.json`,
`tsconfig.json`, `postcss.config.mjs`.

**Raíz:** `.github/workflows/ci.yml`, `VERSION`, `CHANGELOG.md`, `.gitignore`.

Total: 71 archivos, +12 400 / −1 566.

---

## 3. Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| `pytest` con MariaDB 11.8 real | **105 pasan, 0 fallan, 0 omitidas** |
| Línea base antes del trabajo | 20 pasan, **1 omitida** |
| `ruff check app tests` | limpio |
| OpenAPI vs snapshot de `v0.1.0` | **idéntico** |
| Huella de `information_schema` | **idéntica** (62 tablas) |
| `alembic upgrade → downgrade base → upgrade` | reversible |
| `npm run lint` (oxlint + tsc) | limpio |
| `npm run test` (Vitest) | 10 pasan |
| `npm run build` | 8 rutas generadas |
| `docker compose up --build` desde cero | 62 tablas, `/health`, registro, verificación y login correctos; frontend HTTP 200 |

La prueba de Docker se ejecutó en un proyecto Compose **aislado**
(`-p kawsay-smoke`) con volumen propio, y se desmontó con `down -v`. El volumen
de desarrollo `proyecto-integrador_kawsay_mariadb` no se tocó y la pila original
quedó restaurada.

### Defectos encontrados y corregidos durante la implementación

- `test_schema_static::test_api_contract_routes_are_present` leía `main.py` como
  texto: fallaba en cuanto los endpoints salieran de ahí. Reescrita sobre
  `app.openapi()`.
- `test_mariadb_integration` comparaba el total de tablas contra 62 incluyendo
  `alembic_version`, que son 63; habría fallado la primera vez que se ejecutara.
  Además compartía base con el resto y su `downgrade base` habría borrado el
  esquema de las demás pruebas: ahora usa una base propia.
- `write_audit` con `result="FAILURE"` violaba `ck_audit_events_valid_result`
  (admite `SUCCESS`, `DENIED`, `FAILED`). Detectado solo al correr contra
  MariaDB real.
- `.oxlintrc.json` referenciaba la regla `react/react-compiler`, inexistente en
  oxlint 1.80, e impedía que el linter arrancara.
- oxlint encontró 12 problemas en código preexistente, todos corregidos:
  `FormEvent` obsoleto en React 19 (ahora `SubmitEvent`), un `<a>` para
  navegación interna, un ternario usado como sentencia, un control sin etiqueta
  accesible, un import sin usar y tres conversiones inseguras de `FormData`.

---

## 4. Commits

| Hash | Mensaje |
|---|---|
| `b735ecd` | `docs: plan revisado de refactor v0.2.0` |
| `af01805` | `test: red de seguridad y contrato observable de v0.1.0` |
| `396dd46` | `refactor(backend): separa routers y servicios; main.py como factoria` |
| `bd9e80f` | `fix(backend): endurece autenticacion, secretos y reglas duplicadas` |
| `151ceca` | `refactor(frontend): renovacion de sesion, tipos compartidos y lint real` |
| `5651207` | `chore(release): version 0.2.0` |

---

## 5. Decisiones tomadas dentro del alcance

- **Límite de intentos en memoria del proceso.** Una tabla nueva habría
  cambiado el esquema, y un criterio de aceptación es que la huella de
  `information_schema` quede idéntica. Con un solo contenedor de backend el
  límite es efectivo; migrar a Redis o a una tabla queda anotado para v0.3.0.
- **`verification_token` en desarrollo.** Con `APP_ENV=development` se sigue
  devolviendo para el alta nueva, porque no hay servicio de correo y el frontend
  completa el registro con él. Esa diferencia sí distingue un contacto nuevo de
  uno existente, y por eso solo existe en desarrollo: en cualquier otro entorno
  el token nunca viaja en la respuesta.
- **Tipos compartidos en `app/types/api.ts`** y no en `frontend/types/`, porque
  `tsconfig.json` solo typechequea `app/**`.
- **Configuración de oxlint y oxfmt versionada.** Estaba en `.gitignore` como
  residuo del scaffold; ahora `npm run lint` es una compuerta de CI y debe
  comportarse igual en local que en el runner.
- **No se ejecutó `ruff format`** sobre el repositorio: habría reformateado 34
  archivos preexistentes, muy fuera del alcance. La compuerta del proyecto es
  `ruff check`, que pasa limpio.

---

## 6. Trabajo existente conservado

- No se eliminó ningún archivo. `frontend/vite.config.ts` y `frontend/.openai/`
  —que el plan proponía borrar— resultaron estar **sin trackear y ya excluidos**
  por el `.gitignore` de la raíz como «residuos del scaffold inicial», así que
  no forman parte del repositorio y se dejaron intactos en disco. Vitest usa
  `vitest.config.mts`, de modo que no los toca.
- El kit `frontend/components/ui`, `hooks/` y `lib/` sigue ignorado como estaba;
  se verificó que `app/` no importa nada de ahí, por lo que el árbol
  versionado es autosuficiente.
- La base de datos de desarrollo y su volumen Docker no se modificaron. Las
  pruebas usan `kawsay_test` y `kawsay_migration`, creadas para este trabajo.

---

## 7. Limitaciones y asuntos pendientes

1. **CI sin ejecutar todavía en GitHub.** El workflow se creó y el PR está
   abierto, pero su primera ejecución depende del runner. Todas las
   comprobaciones se ejecutaron localmente con los mismos comandos.
2. **Límite de intentos no distribuido.** Con varias réplicas de backend cada
   proceso llevaría su propio contador.
3. **Los commits intermedios no se validaron por separado.** Las fases A y B son
   una división lógica de un refactor atómico: el estado final está verificado
   por completo, pero `af01805` por sí solo no pasaría la batería.
4. **`audio_purge_deadline` y `optional_feature_allowed`** quedan documentadas y
   probadas pero sin punto de uso: no existe carga de audio ni `GET /consents`,
   y añadir esos endpoints habría excedido la superficie HTTP aprobada.
5. **Esquema vectorial dormido.** `source_chunk_embeddings`, `VECTOR(768)` e
   `idx_chunk_embedding` existen pero nada los escribe ni lee. La recuperación
   RAG sigue congelada en coincidencias `LIKE`, según lo acordado.
6. **Recuperación RAG no determinista** cuando la consulta tiene más de ocho
   términos: `list(set(...))[:8]` depende del orden de iteración del conjunto.
   Es comportamiento heredado de `v0.1.0` y se conservó por el congelamiento;
   conviene corregirlo en v0.3.0.
7. **`docker-compose.yml` sigue con secretos literales** para desarrollo local.
   Es coherente con `APP_ENV=development`, y el nuevo guardián impide que esa
   configuración llegue a otro entorno.
8. **Etiqueta `v0.2.0` no creada.** El plan la condiciona a la aprobación del
   PR, que sigue abierto.
