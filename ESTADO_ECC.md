# Estado de Kawsay frente a ECC

**Fecha:** 2026-09-20  
**Repo:** `C:\proyecto-integrador` (árbol de trabajo con v0.8.0 sin commitear)  
**Catálogo:** 292 skills en `C:\Users\NICO\.cursor\skill-repos\ECC\skills`  
**Qué es esto:** informe de estado. No hay diff de corrección, no hay commit.

Se inventariaron las 292 carpetas. Se ejecutaron a fondo las aplicables al stack (FastAPI, Next.js 16, React 19, MariaDB 11.8, PWA, Docker Compose, pytest/vitest). Seis skills de stack ausente se corrieron como lente de ausencia. El resto queda en el apéndice N/A.

**Qué no se hizo:** implementar lo hallado; commitear; escribir exploits o PoCs; entrar en finanzas grupales más allá de anotar el hueco.

---

## Fase 0 — Censo

`skill-stocktake` pide inventariar skills de `~/.claude/skills/`. Aquí se adaptó al catálogo ECC que el plan nombra: una carpeta = una skill. Las 292 existen; no faltó ninguna de las listas oficiales del plan.

| Clase | Criterio | Cantidad |
|---|---|---|
| **ejecutar** | El repo tiene el stack, o la skill es transversal (docs, tests, seguridad, producto, git) | 54 |
| **ausencia** | El stack no está, pero la skill sirve para decidir si falta bien | 6 |
| **meta** | Gobiernan el ritmo de esta auditoría; no juzgan el código | 9 |
| **N/A** | No aporta a comprobar *este* repo | 223 |
| **Total** | | **292** |

Suma: 54 + 6 + 9 + 223 = 292.

### Ejecutar (54)

| Ola | Skills |
|---|---|
| A Superficie | `workspace-surface-audit`, `codebase-onboarding`, `code-tour`, `living-docs-governance`, `documentation-lookup`, `search-first`, `config-gc`, `project-flow-ops` |
| B Arquitectura | `hexagonal-architecture`, `backend-patterns`, `fastapi-patterns`, `python-patterns`, `api-design`, `contract-first`, `architecture-decision-records`, `blueprint`, `product-capability`, `product-lens` |
| C Datos y deploy | `mysql-patterns`, `database-migrations`, `docker-patterns`, `deployment-patterns`, `production-audit`, `error-handling` |
| D Frontend / PWA | `frontend-patterns`, `frontend-design-direction`, `frontend-a11y`, `accessibility`, `react-patterns`, `react-testing`, `react-performance`, `nextjs-turbopack`, `design-system`, `make-interfaces-feel-better`, `content-hash-cache-pattern`, `click-path-audit` |
| E Calidad | `python-testing`, `tdd-workflow`, `e2e-testing`, `browser-qa`, `verification-loop`, `delivery-gate`, `plankton-code-quality`, `coding-standards`, `ai-regression-testing`, `eval-harness`, `iterative-retrieval` |
| F Seguridad y git | `security-review`, `security-scan`, `security-bounty-hunter`, `safety-guard`, `gateguard`, `git-workflow`, `github-ops` |

### Ausencia (6)

`redis-patterns`, `kubernetes-patterns`, `cost-aware-llm-pipeline`, `postgres-patterns`, `seo`, `hipaa-compliance`.

### Meta (9)

`plan-orchestrate`, `parallel-execution-optimizer`, `token-budget-advisor`, `context-budget`, `skill-stocktake`, `skill-comply`, `recursive-decision-ledger`, `ecc-guide`, `ecc-recipes`.

---

## Resumen

Kawsay es un **monolito modular en capas** (routers delgados → servicios dueños del `commit` → modelos SQLAlchemy), no un hexágono con puertos. El mapa del README de raíz coincide con el código en lo gordo (PWA + FastAPI + MariaDB 11.8 + RAG de recuperación + derechos de privacidad) y **diverge donde los docs aún afirman de más**: las purgas «periódicas», las rutas `/diagnostics` de `api-contracts.md`, el `.env.example` del frontend (no existe), `backend/README.md` («búsqueda vectorial» mientras el asistente usa `FULLTEXT`), e `IMPLEMENTATION_REPORT.md` (congelado en v0.2.0 y dice que el PR #1 «no se fusionó»; `gh` lo lista `MERGED`).

v0.8.0 (en el árbol, no en git) hace honesta la PWA en cliente: SW que cachea, `apiCached` con `stale`, escrituras sin cola. Eso está hecho a medias a propósito: solo `/` y `/finanzas` leen el caché.

**Un hallazgo bloquea la promesa de privacidad:** `backend/app/tasks.py` existe y nadie lo programa. El resto es deuda priorizable.

Las olas en paralelo confirmaron el censo (292) y añadieron evidencia que este informe ya incorporó: Compose vivo, click-path de logout/registro/login, segundo `docker-compose.yml`, docs que mienten el PR #1 y el vectorial, `main` remoto sin protección, IndexedDB sin cifrar.

Verificación corrida en esta máquina, 2026-09-20:

| Comando | Resultado |
|---|---|
| `frontend`: `oxlint && tsc --noEmit` | ok |
| `frontend`: `vitest run` | **62** pruebas, 6 archivos |
| `frontend`: `npm audit --omit=dev` | 0 vulnerabilidades |
| `backend`: `ruff check app tests alembic` | ok |
| `backend`: `pytest` sin `TEST_DATABASE_URL` | **87** pasaron, **217** omitidas |
| Docker / Compose (humo) | `GET /health` → `{"status":"ok"}`; `GET http://localhost:3000` → 200 |
| Integración MariaDB y `alembic check` | **no verificados en local**: hay MariaDB de *app*, no `TEST_DATABASE_URL` aislada; no se apuntó pytest a la base viva |

---

## Ola A — Superficie

### workspace-surface-audit

- **Estado skill:** seguida con matices (la skill audita también MCP/plugins de Claude Code; aquí se aplicó a la superficie del *repo*).
- **Severidad:** deuda
- **Hallazgo:** El repo es un monorepo con `frontend/` (Next 16.3.3, React 19.2.6), `backend/` (FastAPI, Python 3.12), `docker-compose.yml` (MariaDB 11.8 + API + PWA) y CI en `.github/workflows/ci.yml`. Hay `backend/.env.example` (nombres de claves, sin valores de producción). El README pide `frontend/.env.example` y **ese archivo no existe**; `NEXT_PUBLIC_API_URL` tiene default en `frontend/app/lib/api.ts`. Secretos locales viven en Compose (`JWT_SECRET`, `CONTENT_ENCRYPTION_KEY`, contraseñas MariaDB) y están pensados para desarrollo. No hay `.mcp.json` ni `AGENTS.md` en el proyecto. ECC está instalado fuera del repo (`skill-repos/ECC`).
- **Huecos:** la skill pediría un inventario de conectores de la máquina; no se listaron valores de entorno.

### codebase-onboarding

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** `README.md` arranca en v0.8.0, Docker, recorrido EMPRENDEDORA, desarrollo sin contenedores, roles RAG y pruebas. `backend/docs/architecture.md` dibuja dominios y retención. `PRUEBAS_POR_ROL.txt` es la guía manual por rol, también en v0.8.0. Una persona nueva puede levantar el sistema si Docker está arriba. El onboarding **no avisa** que `tasks.py` no corre solo, ni que el diagnóstico del diccionario no tiene API, ni que el frontend no trae `.env.example`.
- **Huecos:** no hay `CONTRIBUTING.md`; el primer commit útil de un extraño tropieza con docs a medias.

### code-tour

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** El tour real es: `frontend/app/` (pantallas por ruta), `frontend/app/lib/` (cliente HTTP, navegación, caché), `backend/app/main.py` (composición, 73 líneas), `backend/app/routers/` (HTTP), `backend/app/services/` (casos de uso), `backend/app/models/` (62 tablas), `backend/app/api_contracts.py` (Pydantic), `backend/alembic/versions/` (`0001`, `0002`), `backend/tests/` (capas, contratos, matriz, RAG, evaluación). `frontend/app/page.tsx` reimplementa el cascarón en vez de usar `AppShell`.
- **Huecos:** no hay un `CODE_TOUR.md`; el tour está implícito en architecture + este informe.

### living-docs-governance

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Los docs vivos que coinciden con v0.8.0 son `README.md` de raíz, `CHANGELOG.md`, `VERSION` y `PRUEBAS_POR_ROL.txt`. Los que **no** se gobiernan: `IMPLEMENTATION_REPORT.md` (congelado en v0.2.0; afirma que el PR #1 «no se fusionó» y `gh` lo lista `MERGED`), `backend/docs/api-contracts.md` (sigue prometiendo `/diagnostics` y `/formalization-routes`; esos routers no existen), `backend/README.md` (promete «búsqueda vectorial»; `assistant_service.py` usa `FULLTEXT` y deja VECTOR dormido), `PLAN_v0.8.0.md` (sigue «propuesto» con el código ya en el árbol), `architecture.md` («se purgan periódicamente» — la función existe, el programador no), `graphify-out/GRAPH_REPORT.md` (mapa de 2026-08-31, habla de UI que ya no está).
- **Huecos:** no hay dueño ni caducidad de documentos.

### documentation-lookup

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Para una pregunta de dominio, el orden útil es `architecture.md` → `api_contracts.py` → router → service. Para una pregunta de producto, `PRUEBAS_POR_ROL.txt` y `CHANGELOG.md`. `api-contracts.md` **no** es fuente fiable: describe rutas que el OpenAPI actual no tiene. El snapshot vivo está en `backend/tests/contracts/openapi_v0_2.json` más `APPROVED_NEW_OPERATIONS` en `test_contracts.py`.
- **Huecos:** dos «contratos» escritos (markdown vs Pydantic); gana el código.

### search-first

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** El árbol es buscable: permisos en `authorization.py` y `navigation.ts`, operaciones en `routers/`, reglas de dominio en `domain_rules.py`. No hace falta adivinar. El índice `FULLTEXT` se usa en `assistant_service.py` (v0.7.0); el vectorial no.
- **Huecos:** ninguno material.

### config-gc

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Basura de configuración que sigue viva: `CORS_ORIGINS` default e `.env.example` incluyen `http://localhost:5173` (Vite; este frontend es Next en `:3000`). Conviven **dos** Compose (`docker-compose.yml` raíz con `change_me_local` y `backend/docker-compose.yml` con `change_me` / otro volumen). El plan v0.8.0 acusó a `Geist_Mono` de no usarse; `font-mono` sí aparece en evaluación/admin/auditoría, la fuente se quedó y eso es correcto. El manifiesto SVG se sustituyó por `app/manifest.ts` + PNG.
- **Huecos:** no se barrió `5173` ni el example de admin URL.

### project-flow-ops

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** El flujo declarado es semver (`VERSION`, `CHANGELOG`) + CI en `main`/PR + planes por versión (`PLAN_v0.8.0.md`, `PLAN_REFACTOR_MVC_v0.2.0.md`). CI es el gate real (ruff, pytest sin skipped, lint, build, `docker compose up` + `/health`). El flujo **roto** hoy: v0.8.0 está en el working tree y no en git; el plan sigue en «propuesto».
- **Huecos:** no hay issue tracker en el repo; el siguiente paso operativo es commitear o descartar, no auditar más.

**¿El mapa coincide con v0.8.0?** En el recuento de piezas, sí. En tres promesas (purga automática, diagnóstico por API, onboarding frontend con `.env.example`), no.

---

## Ola B — Arquitectura, API y producto

### hexagonal-architecture

- **Estado skill:** seguida con matices (el repo no es hexagonal; la skill se usó como plantilla de fronteras).
- **Severidad:** ok
- **Hallazgo:** No hay puertos ni adapters. Los servicios importan modelos SQLAlchemy y hacen `commit`. Eso es un monolito modular en capas, y `backend/tests/test_architecture.py` lo clava: routers sin SQLAlchemy ni `app.models`; servicios sin FastAPI/Starlette; `domain_rules.py` y `core/clock.py` / `core/exceptions.py` solo stdlib; `main.py` ≤ 80 líneas y sin endpoints. Para el tamaño actual (un proceso, una base, una UI) invertir a hexágono sería teatro. El dominio puro existe (`domain_rules`) y el resto orquesta I/O.
- **Huecos:** la skill pediría `UserRepositoryPort`; no está y no hace falta todavía.

### backend-patterns

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** Un motor (`database.py`: `pool_pre_ping`, `pool_recycle=1800`), sesiones por request (`get_db`), servicios que poseen la transacción, auditoría escrita desde el caso de uso (`write_audit`). `owned_business` mete la propiedad en el `WHERE`. Rate-limit en memoria documentado para un solo contenedor (`rate_limit.py`).
- **Huecos:** no hay capa de repositorio (decisión consciente, v0.2.0). `tasks.py` usa `SessionLocal` por su cuenta: otro proceso implícito que no existe.

### fastapi-patterns

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** `create_app()` registra 11 módulos de router, un `exception_handler` de `AppError` → `{"detail": ...}`, CORS por lista. Routers delgados (ejemplo: `businesses.py` son cuatro funciones que delegan). OpenAPI sale de los `response_model`. `/health` es estático (`system.py`).
- **Huecos:** no hay versionado de API (`/v1`); aceptable en 0.x.

### python-patterns

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** 3.12, Pydantic v2 / `pydantic-settings`, type hints, ruff limpio sobre `app tests alembic`. UUIDs y `utc_now()` centralizados. Sin `datetime.utcnow()` a la vista del núcleo (eso se corrigió en v0.2.0).
- **Huecos:** ninguno material en el backend de aplicación.

### api-design

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Recursos claros (`/businesses`, `/finance/movements`, `/assistant/query`, `/privacy/export`, `/evaluation/sets`). 404 horizontal en negocio ajeno (`authorization.py`, `owned_business`). Registro no enumera cuentas (`REGISTRATION_MESSAGE` único). El documento `api-contracts.md` lista `/diagnostics` y `/formalization-routes` que **no están** en los routers. La tabla de evaluación vive bajo `/evaluation/*`, no bajo `/evaluations` como dice ese markdown.
- **Huecos:** contrato escrito ≠ OpenAPI; memberships y organizations sin superficie HTTP.

### contract-first

- **Estado skill:** seguida con matices
- **Severidad:** deuda
- **Hallazgo:** La fuente de verdad es `backend/app/api_contracts.py`. `test_contracts.py` impide borrar operaciones del snapshot `openapi_v0_2.json` y exige declarar las nuevas. El frontend **copia a mano** `frontend/app/types/api.ts` (comentario propio: antes cada página redeclaraba tipos). No hay generación OpenAPI → TypeScript. Los nombres no coinciden (`UserView` vs `User`, `RegistrationResult` vs `Registration`, `ConsentStatusView` vs `ConsentStatus`).
- **Huecos:** un cambio de campo en Pydantic no rompe `tsc` hasta que alguien actualice el `.ts`.

### architecture-decision-records

- **Estado skill:** seguida con matices (la skill exige `docs/adr/ADR-NNNN`; **no existe**)
- **Severidad:** deuda
- **Hallazgo:** Cero archivos ADR. Las decisiones viven en `CHANGELOG.md`, planes y docstrings (`rate_limit.py` explica por qué no Redis; `assistant_service.py` explica por qué el VECTOR duerme; el plan v0.2.0 registra «sin repositorios»). Eso funciona mientras el equipo es uno. No escala a «por qué MariaDB y no Postgres» sin releer tres sitios.
- **Huecos:** no hay `docs/adr/`.

### blueprint

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** `architecture.md` es el blueprint: dominios, ER, retención, diccionario. Compose es el blueprint de deploy (tres servicios, un volumen). El hueco del blueprint es operativo: dibuja purga y diagnóstico como si existieran en runtime.
- **Huecos:** no hay diagrama de procesos (API + worker); porque el worker no está.

### product-capability

- **Estado skill:** seguida con matices (no hay `PRODUCT.md` ni `docs/product/`)
- **Severidad:** deuda
- **Hallazgo:** Capacidad **entregada** a EMPRENDEDORA: cuenta, negocio propio, libro, costos/precio, asistente que cita o se abstiene, consentimientos, exportación síncrona, baja lógica. Capacidad **entregada** a curaduría/auditoría/admin: fuentes, banco `/evaluation`, alertas, suspensión. Capacidad **en esquema y no en producto**: `business_memberships` (OWNER/COLLABORATOR/VIEWER; se escribe OWNER al crear y no se lee para autorizar), `organizations` / `organization_memberships`, diagnóstico y rutas de formalización, embeddings VECTOR(768), `background_jobs`. Finanzas grupales serían producto nuevo sobre memberships; **fuera de esta auditoría**.
- **Huecos:** tablas reservadas sin API ni pantalla.

### product-lens

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** La promesa pública (PWA para emprendedoras bolivianas con red intermitente) y v0.8.0 del árbol se alinean en inicio y finanzas. El asistente, privacidad, curaduría y evaluación **siguen mintiendo o fallando en silencio sin red**, porque no usan `apiCached`. El derecho al olvido se *agenda* (`purge_due_at`) y no se *ejecuta*. Eso, visto como producto, es una promesa a medias.
- **Huecos:** no se midió usabilidad con usuarias reales en esta auditoría.

---

## Ola C — Datos y despliegue

### mysql-patterns

- **Estado skill:** seguida (MariaDB 11.8, no MySQL Oracle)
- **Severidad:** ok (localmente **no verificado** contra el motor)
- **Hallazgo:** Compose y CI clavan `mariadb:11.8`, `utf8mb4_unicode_ci`, TZ UTC. El esquema usa `FULLTEXT` en `source_chunks` y `VECTOR(768)` + `VECTOR INDEX` en embeddings (`0001_initial_schema.py`, `models/base.py`). Dinero en `Decimal`. Soft-delete + `deleted_at` en el filtro de negocio. `information_schema` no se sustituye por SQLite: `conftest.py` lo dice y CI lo cumple. `pool_pre_ping` está. No se corrió `SELECT VERSION()` aquí: Docker no se levantó.
- **Huecos:** VECTOR existe y no se consulta; es aplazamiento documentado, no olvido.

### database-migrations

- **Estado skill:** seguida
- **Severidad:** ok (check de deriva **no verificado en local**)
- **Hallazgo:** Alembic, dos revisiones (`0001` esquema, `0002` permiso `business.manage_own`). CI hace `alembic upgrade head` y `alembic check`. `seeds.sql` quedó alineado con `business.manage_own` en el árbol v0.8.0. La imagen del backend corre `alembic upgrade head && uvicorn`.
- **Huecos:** v0.8.0 no toca esquema (correcto). Sin MariaDB local no se afirma que `alembic check` pase hoy.

### docker-patterns

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Tres servicios, healthcheck de MariaDB, backend espera `service_healthy`, frontend `npm ci` + `next build` + `next start`. Backend: `python:3.12-slim`, un proceso, **sin** `USER` no-root ni `HEALTHCHECK` de imagen. Frontend: `node:22-alpine`; `depends_on: backend` no espera salud. El puerto `3306:3306` se publica a todas las interfaces. Convive `backend/docker-compose.yml` (otro volumen, otras claves). CI tiene job `docker compose up --build` y `curl /health`. **No hay** servicio ni sidecar que ejecute `python -m app.tasks`. Secretos de desarrollo en claro en Compose (esperado; README lo admite).
- **Huecos:** un solo proceso backend; rate-limit y tareas asumen eso.

### deployment-patterns

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** El «despliegue» real es Compose en una máquina. No hay TLS, no hay objeto store, no hay backups verificados (README lo lista como límite). `APP_ENV=development` en Compose: el guardián de secretos (`reject_placeholder_secrets`) **no** corre en ese modo. Un `APP_ENV=production` con los literales de ejemplo no arranca: eso está bien. No hay staging, no hay canary, no hay ingress.
- **Huecos:** no hay runbook de producción más allá del README.

### production-audit

- **Estado skill:** seguida
- **Severidad:** bloquea (si se afirma «listo para producción»)
- **Hallazgo:** `/health` no toca la base (`system.py` devuelve `{"status":"ok","service":"pwa-autonomia-backend"}`). El job Docker de CI se pone verde con un proceso vivo y una base que *en el arranque* migró; un MariaDB que muere después no se ve. Purgas no programadas. Rate-limit se pierde al reiniciar el contenedor. Tokens en `sessionStorage`. CORS de desarrollo. Sin HTTPS. Eso no es un fallo del MVP académico; **sí** es un no-go de producción.
- **Huecos:** health de dependencias, worker, secretos de host, backups.

### error-handling

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** `AppError` y subclases en `core/exceptions.py`; un handler. El cliente distingue fallo de red (`NetworkError`, `isFetchFailure`) de HTTP (`toError`). v0.8.0 deja de mostrar `TypeError: Failed to fetch` y deja de pintar `Bs 0,00` cuando no hay resumen. POST offline lanza `OFFLINE_WRITE_ERROR` y no encola. Los 404 de negocio ajeno no distinguen existencia.
- **Huecos:** pantallas que aún usan `api()` (asistente, privacidad, admin) siguen sin estado stale honesto.

---

## Ola D — Frontend, accesibilidad y PWA

### frontend-patterns

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** App Router, páginas `'use client'`, un cliente `api`/`apiCached`, navegación por permisos (`navigation.ts`). No hay store global. `AppShell` y `page.tsx` duplican el cascarón (el comentario de `NAV_LINKS` dice que la lista *ya no* está duplicada; el *layout* sí). Páginas grandes: `curaduria/page.tsx` ~634 líneas, `evaluacion/page.tsx` ~534, `finanzas/page.tsx` ~459, `administracion/page.tsx` ~414, `page.tsx` ~391.
- **Huecos:** extraer shell único y partir curaduría/evaluación.

### frontend-design-direction

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** Dirección visual coherente: heading, primary `#642447` / sidebar teal, cards, copy en español boliviano, dinero `es-BO`. Manifiesto y tema alineados (`manifest.ts`). No hay marca paralela.
- **Huecos:** no hay guía de voz escrita (`brand-voice` es N/A y se nota poco).

### frontend-a11y

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Login envuelve inputs en `<label>` (asociación implícita). Errores con `role="alert"` en login/registro/finanzas; no en evaluación, asistente ni privacidad. Banner offline es `<output>` (evita `prefer-tag-over-role`). `aria-live` en carga de inicio/finanzas. **Regresión conocida:** el `<aside>` de nav usa `-translate-x-full` y **sigue en el árbol**; los `Link` son enfocables con el menú cerrado (`app-shell.tsx`, `page.tsx`). El aside vive **dentro de `<main>`** (landmark incorrecto). No hay `aria-expanded`, Escape ni trampa de foco. `AppShell` no pone `aria-label` en `<nav>` (Inicio sí). `htmlFor`/`id` casi no se usan.
- **Huecos:** cajón, skip link, auditoría axe. Fuera de v0.8.0 a propósito.

### accessibility

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Igual que `frontend-a11y` a escala de producto: preferencias de accesibilidad existen en esquema (`user_preferences`) y architecture las menciona; no se auditó una pantalla de ajuste de fuente/voz en esta ola. El copy evita jerga innecesaria. No hay i18n (español único: correcto para el piloto).
- **Huecos:** WCAG formal no corrido.

### react-patterns

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Client components, `useState`/`useEffect` para fetch. v0.8.0 evitó `setState` en efecto para el resumen (se deriva `visibleSummary`). No hay Context más que sesión. Las pantallas admin/curaduría mezclan fetch, formularios y tablas en un archivo.
- **Huecos:** extraer hooks de datos; no es bloqueo.

### react-testing

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** Vitest 4, 62 pruebas: `api` (tokens, refresh, red, `apiCached`), offline/staleness, navegación por permiso, evaluación (métricas de corrida). No hay Testing Library ni pruebas de componente. CI corre `npm run test`.
- **Huecos:** cero pruebas del cajón, del banner, de `AppShell`.

### react-performance

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** Listas cortas (movimientos recientes, costos). No hay virtualización y no hace falta. El riesgo no es FPS: es JS de páginas de 500–600 líneas y el SW sirviendo shell. `/_next/static` va cache-first (hash en el nombre).
- **Huecos:** no se perfiló en dispositivo bajo.

### nextjs-turbopack

- **Estado skill:** seguida con matices (no hay config Turbopack específica; Next 16 la trae al `dev`)
- **Severidad:** ok
- **Hallazgo:** `next.config.ts` solo pone `experimental.useOffline` y cabeceras (`nosniff`, `DENY`, referrer, permissions-policy, CSP del `sw.js`). `package.json`: `next dev` / `next build` / `next start`. La doc de Next deja `fetch()` del cliente fuera del retry de `useOffline`; el código lo respeta (`CHANGELOG` 0.8.0).
- **Huecos:** ninguno.

### design-system

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Tailwind 4 + tokens (`bg-background`, `font-heading`, `rounded-xl`). No hay librería de componentes propia más que `AppShell`, `AuthFrame`, `OfflineBanner`. Cada página inventa la card otra vez. No es grave en un MVP; es donde crece el desvío visual.
- **Huecos:** no hay Storybook (y no se pide).

### make-interfaces-feel-better

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** v0.8.0 arregló la mentira peor (saldo cero sin datos) y el doble envío (botones `disabled` mientras `saving`). Mensajes de red en español. Banner de offline en el layout, cubre también el inicio. Pendiente: la sensación de «instalada y útil» en asistente/privacidad sin red.
- **Huecos:** `apiCached` incompleto.

### content-hash-cache-pattern

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** Next emite `/_next/static/...` con hash. `sw.js` (`kawsay-shell-v2`) hace cache-first de esos assets, network-first de documentos con fallback `/offline`, y **no intercepta** orígenes distintos (la API queda fuera). `sw.js` tiene `Cache-Control: no-store`. Precache: `/`, `/offline`, favicon, iconos PNG.
- **Huecos:** primer load offline de una ruta nunca visitada cae a `/offline` (correcto, documentado).

### click-path-audit

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Camino EMPRENDEDORA: `/registro` → (auto-verifica en dev) → `/emprendimiento` → `/finanzas` → `/asistente` → `/privacidad`. Nav filtrada por permiso (`visibleLinks`). Una usuaria sin permisos solo ve Privacidad (`firstAllowedHref`). Curaduría / evaluación / administración no aparecen sin el permiso. Tres roturas de camino: (1) `/registro` siempre hace `push('/emprendimiento')`, no `firstAllowedHref`; (2) login llama `saveTokens` **antes** de `/me` — si el perfil falla, queda sesión y error en pantalla; (3) en Inicio el botón «Cerrar sesión» es `hidden sm:block` y el aside **no** tiene logout, así que en móvil no hay salida (`AppShell` sí la tiene al pie). El cajón cerrado sigue tabulable. Escritura offline: el camino se detiene con mensaje, no con cola (decisión de v0.8.0).
- **Huecos:** no se recorrió el camino en navegador en *esta* sesión (sí en la implementación de v0.8.0).

---

## Ola E — Calidad y verificación

### python-testing

- **Estado skill:** seguida (se corrió pytest)
- **Severidad:** deuda (local) / ok (diseño de CI)
- **Hallazgo:** 87 unitarias/estáticas pasaron aquí. 217 se omiten sin `TEST_DATABASE_URL`: administración, matriz de autorización, acceso horizontal, RAG, evaluación persistida, privacidad, finanzas, smoke HTTP, ciclo de migración. CI **prohíbe** skipped. Compose tiene MariaDB de *aplicación* arriba; no se usó como base de prueba (correcto: no es aislada). Esta máquina no es verde de integración, y no se fingió.
- **Huecos:** sin `TEST_DATABASE_URL` / `TEST_MIGRATION_DATABASE_URL` desechables no se afirma el esquema real hoy.

### tdd-workflow

- **Estado skill:** seguida con matices (el repo prueba mucho; no practica TDD estricto)
- **Severidad:** ok
- **Hallazgo:** Hay pruebas que *gobiernan* el diseño: capas por AST, snapshot OpenAPI, huella de `information_schema`, matriz de permisos, «purga y exportación no se desincronizan» (`test_data_export.py` parsea `tasks.py`). v0.8.0 trajo `test_version_sync.py` y `offline.test.ts`. El orden histórico es plan → código → prueba, no red-green-refactor puro.
- **Huecos:** no hay gancho que obligue a escribir la prueba primero.

### e2e-testing

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Cero Playwright/Cypress. `windows-desktop-e2e` es N/A. La guía `PRUEBAS_POR_ROL.txt` es e2e **manual**. CI no abre un navegador.
- **Huecos:** un humo de registro+login+movimiento cubriría lo que la PWA acaba de cambiar.

### browser-qa

- **Estado skill:** seguida con matices
- **Severidad:** deuda
- **Hallazgo:** Compose respondió en esta máquina: `/health` ok y `/` 200. No hay baselines visuales, axe ni pases de teclado. La implementación de v0.8.0 sí verificó SW, `/offline`, banner e iconos. Esta auditoría **no** vuelve a afirmar ese recorrido de PWA.
- **Huecos:** re-correr EMPRENDEDORA online/offline cuando el stack esté levantado.

### verification-loop

- **Estado skill:** seguida (aplicada al informe y a los comandos)
- **Severidad:** ok
- **Hallazgo:** Lint/test frontend verdes. Ruff verde. Pytest local honesto (skipped visibles). Skills aplicables tienen tarjeta. Skills en blanco: ninguna de las 54+6. Docker/MariaDB marcados no verificados, no verdes.
- **Huecos:** el loop de producto (usuaria real + fuentes publicadas) no se corrió.

### delivery-gate

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** El gate de *main* es CI completo. El gate de *este árbol* no: v0.8.0 no está commiteado, integración local no corre, Compose no se levantó. **No se recomienda fusionar con la etiqueta «verificado de punta a punta»** hasta CI en un PR.
- **Huecos:** el propio `PLAN_v0.8.0.md` sigue en propuesto.

### plankton-code-quality

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** El backend está limpio de capas cruzadas (pruebas AST). El frontend acumula páginas-dios (curaduría, evaluación). `tasks.py` es un tercer modo de proceso sin hogar. Duplicación AppShell / inicio.
- **Huecos:** no se midió complejidad ciclomática; el tamaño de archivo basta.

### coding-standards

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** ruff + oxlint + `tsc --noEmit` en CI. Estilo de docstrings en español que explican *por qué*. Nombres de permiso con punto (`business.manage_own`).
- **Huecos:** oxfmt existe (`format:check`) y no está en CI.

### ai-regression-testing

- **Estado skill:** seguida con matices (no hay agente LLM que regresar; hay asistente de recuperación)
- **Severidad:** ok
- **Hallazgo:** El banco `/evaluation` (v0.7.0) es la regresión: categorías cerradas, corrida síncrona, mismo `evaluate_message` que la usuaria, sin persistir conversación. `MODEL_NAME = "retrieval-only-mvp"`, `MODEL_VERSION = "v2"`. Eso es exactamente la skill aplicada al producto, no a Claude.
- **Huecos:** no hay corrida de evaluación ejecutada en esta máquina (hace falta MariaDB + fuentes).

### eval-harness

- **Estado skill:** seguida con matices (la skill ECC habla de evals de Claude Code; se aplicó al banco `/evaluation`)
- **Severidad:** ok
- **Hallazgo:** `evaluation_service.py` deriva el criterio de `category` (`FORMALIZATION`, `FINANCE`, `MARKETING` vs abstención/advertencia). Tope 200 casos. Escritura `source.review`, lectura también `audit.read`. Front en `/evaluacion` (~534 líneas). Hay `backend/scripts/compare_retrieval.py`.
- **Huecos:** la skill pide pass@k de agentes; no aplica.

### iterative-retrieval

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** v0.7.0 cambió `LIKE` → `FULLTEXT` (`sqlalchemy.dialects.mysql.match`) y lo midió. VECTOR(768) queda para el siguiente salto, ahora medible. Abstención si no hay evidencia (`ABSTENTION_ANSWER`). Términos normativos disparan advertencia.
- **Huecos:** no hay query rewriting ni rerank; no hacen falta hasta tener corpus y baseline.

---

## Ola F — Seguridad y git

Sin exploits, sin PoCs, sin payloads. Solo hallazgos y endurecimiento de alto nivel.

### security-review

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** JWT de acceso 15 min + refresh opaco 30 días, **rotado** al canjear (`auth_service.refresh` revoca y emite; no hay detección de reuso de familia). Hash Argon2id. Refresh guardado como hash. Notas y textos con Fernet (clave derivada de SHA-256 de `CONTENT_ENCRYPTION_KEY`). Registro no enumera. Rate-limit por contacto e IP, en memoria. 404 horizontal. Guardián de secretos fuera de `development`. Cabeceras en Next; CSP solo en `/sw.js`. Tokens en **`sessionStorage`**: un XSS en la PWA los lee; no hay cookie `HttpOnly`. IndexedDB (`kawsay-offline`) guarda JSON de GET (saldos, movimientos) **sin cifrar**; se limpia al cerrar sesión (`clearTokens` → `clearOfflineCache`). CORS: orígenes listados (no `*`), métodos y headers `*`; el default incluye `:5173`. Compose y CI llevan secretos de laboratorio en claro (locales / efímeros).
- **Huecos:** cookie + CSRF o endurecer XSS; quitar `:5173`; no tratar Compose como producción.

### security-scan

- **Estado skill:** seguida (superficie, no scanner de red)
- **Severidad:** ok
- **Hallazgo:** `npm audit --omit=dev` → 0. La skill ECC de scan apunta a `.claude/` + AgentShield: **este repo no tiene `.claude/`**, así que ese modo no aplica. Ruff no es SAST de secretos; no se imprimieron valores. `.env` está en `.gitignore` (raíz y `frontend/.env*`). `backend/.env.example` usa marcadores `replace-with-...`. No se ejecutó un volcado de historial git en busca de claves.
- **Huecos:** no hay gitleaks/bandit en CI.

### security-bounty-hunter

- **Estado skill:** seguida en modo defensivo (caza de *clases* de bug, no de PoC)
- **Severidad:** deuda
- **Hallazgo:** Clases abiertas, sin pasos de ataque: (1) XSS → robo de sesión por `sessionStorage`; (2) rate-limit en RAM → se resetea con el proceso y no se comparte; (3) `/health` mentiroso si la base cae a mitad de vida; (4) purga no corre → datos «borrados» siguen en disco después del plazo; (5) memberships no autorizan → hoy solo owner, mañana un COLLABORATOR escrito a mano no vería el negocio (fallo de producto, no de fuga). Acceso horizontal cubierto por pruebas *cuando* MariaDB está.
- **Huecos:** la skill de bounty pediría reproducir; aquí está prohibido.

### safety-guard

- **Estado skill:** seguida
- **Severidad:** ok
- **Hallazgo:** El asistente se abstiene sin evidencia y advierte en normativo. No hay generación libre. Escrituras offline se rechazan (no se inventa un libro). Exportación y baja existen como API. Público: adultas emprendedoras; no hay superficie de menores. Fuera de scope: bio, armas, crime-help.
- **Huecos:** ninguno para el piloto.

### gateguard

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** CI es un buen guardia: MariaDB real, `alembic check`, fail-on-skip, lint, test, build, Compose+health. El working tree actual **no pasó ese guardia** todavía. Un merge de v0.8.0 sin PR sería saltarse el único gate.
- **Huecos:** oxfmt y npm audit no están en el workflow.

### git-workflow

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** El historial remoto sigue ramas `feat/v0.x.0` y PRs #1–#6. Lo actual lo rompe: v0.8.0 está escrito **encima de `main`** (`VERSION`, `CHANGELOG`, `main.py`, `package.json`) sin rama `feat/v0.8.0` y sin PR. `PLAN_v0.8.0.md` sigue «propuesto». Esta auditoría añade `ESTADO_ECC.md` y no commitea. El flujo sano es: rama, commit de v0.8.0, PR, CI verde. No se usó `--amend` ni force.
- **Huecos:** `main` local no está desplegable; el remoto sigue en v0.7.0.

### github-ops

- **Estado skill:** seguida
- **Severidad:** deuda
- **Hallazgo:** Repo público `Nicolas-hugo-work/integrador-emprendedoras`. CI en `main`/PR (pytest+ruff+MariaDB, lint/test/build, Compose+`/health`); el último verde es v0.7.0, no ha visto este árbol. `gh` lista #1–#6 `MERGED`, cero PRs/issues abiertos. `main` **sin protección de rama**. Dependabot y alertas de vulnerabilidad **deshabilitados**; secret scanning y push protection sí. No hay `SECURITY.md` ni CODEOWNERS.
- **Huecos:** oxfmt, `npm audit` y pip-audit no están en el workflow.

---

## Ola G — Lentes de ausencia

### redis-patterns

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** ausencia correcta
- **Severidad:** ok
- **Hallazgo:** Un contenedor backend (`docker-compose.yml`). El limitador lo dice: en memoria a propósito, para no tocar el esquema. Redis aportaría rate-limit compartido y cola de `tasks.py`. Hoy no hay segundo proceso ni réplica. **Cuando** haya más de un worker, Redis (o una tabla) deja de ser opcional para el 429. Hasta entonces añade operador sin usuario.

### kubernetes-patterns

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** ausencia correcta
- **Severidad:** ok
- **Hallazgo:** Tres procesos y un volumen. Compose + CI que levanta Compose es el nivel correcto. K8s sin un equipo de plataforma es costo. El hueco de orquestación real es un *cron* o un segundo contenedor para `tasks.py`, no un cluster.

### cost-aware-llm-pipeline

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** ausencia correcta (aplazada a propósito)
- **Severidad:** ok
- **Hallazgo:** README y `assistant_service.py`: recuperación segura, sin proveedor generativo. `MODEL_NAME = "retrieval-only-mvp"`. VECTOR dormido. No hay tokens de OpenAI/Anthropic en el example. Meter un LLM ahora sin corpus publicado ni eval de *generación* solo gasta. El banco de evaluación ya está listo para cuando exista.

### postgres-patterns

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** ausencia correcta
- **Severidad:** ok
- **Hallazgo:** MariaDB 11.8 no es un olvido de Postgres: `FULLTEXT` + `VECTOR(768)` nativos están en `0001` y en las pruebas de huella. Migrar a PG tiraría esas piezas y el snapshot de 62 tablas. La skill de Postgres no debe usarse para «corregir» el dialecto.

### seo

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** ausencia correcta
- **Severidad:** ok
- **Hallazgo:** PWA autenticada, `start_url` `/`, sin marketing público. Login/registro no son landings indexables a propósito. `lang: es` en el manifiesto basta. SEO de contenidos sería otro producto.

### hipaa-compliance

- **Estado skill:** seguida en modo ausencia
- **Veredicto:** irrelevante como régimen; útil como contraste
- **Severidad:** ok
- **Hallazgo:** Piloto académico en Bolivia, no covered entity HIPAA. La skill sirve para mirar cifrado (Fernet en notas/mensajes), exportación (`/privacy/export`), borrado (agenda sin worker) y auditoría seudonimizada (`architecture.md`). El contraste: HIPAA exigiría BAA, acceso mínimo operativo, y la purga **real**. Eso refuerza el hallazgo de `tasks.py`, no pide un programa HIPAA.

---

## Skills meta (no juzgan el código)

| Skill | Uso en esta auditoría |
|---|---|
| `skill-stocktake` | Censo de 292; no se corrieron sus scripts contra `~/.claude/skills` |
| `skill-comply` | Clasificación ejecutar / ausencia / N/A según el plan |
| `plan-orchestrate` | Olas A–G + informe; sin skills de implementación (`orch-*`) |
| `parallel-execution-optimizer` | Olas concurrentes; síntesis al cierre |
| `token-budget-advisor` / `context-budget` | No se leyeron las 292 `SKILL.md` enteras: sí las aplicables y las de ausencia |
| `recursive-decision-ledger` | Sección siguiente |
| `ecc-guide` / `ecc-recipes` | Receta: censo → ejecutar aplicables → lente de ausencia → ledger → apéndice |

---

## Ledger de decisiones abiertas

Ordenadas por daño si se ignora. Finanzas grupales se anotan y se detienen.

| # | Decisión | Por qué está abierta | Si se ignora |
|---|---|---|---|
| 1 | **Programar `tasks.py`** (cron, sidecar o `background_jobs`) | `purge_due_accounts`, audio y sesiones no corren. architecture y README hablan de purga periódica. | El derecho al olvido es un timestamp. **Bloquea** cualquier afirmación de producción / privacidad cumplida. |
| 2 | **Dónde viven los tokens** (`sessionStorage` vs cookie `HttpOnly`) | XSS = sesión. PWA + SW amplían la superficie. | Un fallo de script en Next entrega la cuenta. Deuda alta, no el siguiente commit de v0.8.0. |
| 3 | **Terminar `apiCached`** (asistente, privacidad, emprendimiento; admin opcional) | v0.8.0 solo cubrió `/` y `/finanzas`. | Sin red, esas pantallas vuelven al silencio o al error inglés-HTTP. Deuda de honestidad. |
| 4 | **Una sola fuente de tipos** (OpenAPI → TS, o Zod compartido) | `api_contracts.py` ≠ `frontend/app/types/api.ts`. | El front acepta o pierde campos en silencio. |
| 5 | **`/health` con dependencia** (SELECT 1 o ping al pool) | CI y Compose solo miran el proceso. | MariaDB caído + API «ok». |
| 6 | **Cajón no enfocable + logout en Inicio móvil** | Tab entra al nav off-screen; «Cerrar sesión» es `hidden sm:block` y el aside de Inicio no tiene logout. | En móvil no se sale de la sesión desde la primera pantalla. |
| 7 | **Partir curaduría / evaluación / admin** | 400–630 líneas, `'use client'`, `api()` crudo. | Cada feature de corpus/eval sale más cara y sin offline honesto. |
| 8 | **Qué hacer con el esquema dormido** (memberships, organizations, diagnóstico, VECTOR) | Está modelado, se siembra OWNER, no autoriza. | O se documenta como reserva (ADR) o alguien «activa» finanzas grupales mal. **No implementar finanzas grupales ahora.** |

Fuera del ledger, basura chica: quitar `:5173` de CORS; unificar o borrar `backend/docker-compose.yml`; crear o dejar de mencionar `frontend/.env.example`; caducar `IMPLEMENTATION_REPORT.md`, `backend/README.md` (vectorial) y `api-contracts.md`; sacar v0.8.0 a `feat/v0.8.0` y no commitear este informe en el mismo commit.

---

## Cierre de `verification-loop` + `delivery-gate` sobre este informe

- [x] 292 carpetas contadas y clasificadas (54 / 6 / 9 / 223)
- [x] Las 54 ejecutables tienen tarjeta con evidencia
- [x] Las 6 de ausencia tienen veredicto
- [x] Ninguna skill aplicable en blanco
- [x] Comandos de lint/test corridos; humo de Compose sí; integración MariaDB **no** pintada de verde
- [x] Sin exploits
- [x] Sin implementación ni commit de correcciones
- [x] Finanzas grupales: hueco de producto, detenido
- [x] Apéndice N/A por familia

**Gate de entrega del informe:** cumple.  
**Gate de entrega de Kawsay v0.8.0:** no forma parte de este documento; el código está en el árbol y CI no lo ha visto.

---

## Apéndice — 223 N/A por familia

Una línea de razón por familia. Las skills de implementación ECC (`orch-add-feature`, `orch-build-mvp`, `orch-fix-defect`, etc.) están aquí a propósito: el plan las excluyó para no «arreglar» lo hallado.

### Swift / iOS (5)

No hay target Apple.  
`ios-icon-gen`, `swift-actor-persistence`, `swift-concurrency-6-2`, `swift-protocol-di-testing`, `swiftui-patterns`

### Android / Kotlin / Flutter / React Native / Compose (10)

No hay cliente móvil nativo; la PWA es Next.  
`android-clean-architecture`, `compose-multiplatform-patterns`, `dart-flutter-patterns`, `flutter-dart-code-review`, `kotlin-coroutines-flows`, `kotlin-exposed-patterns`, `kotlin-ktor-patterns`, `kotlin-patterns`, `kotlin-testing`, `react-native-patterns`

### Spring / Quarkus / Java (10)

El backend es FastAPI.  
`java-coding-standards`, `jpa-patterns`, `quarkus-patterns`, `quarkus-security`, `quarkus-tdd`, `quarkus-verification`, `springboot-patterns`, `springboot-security`, `springboot-tdd`, `springboot-verification`

### Django (5)

No hay Django.  
`django-celery`, `django-patterns`, `django-security`, `django-tdd`, `django-verification`

### Laravel / Rails (6)

No hay PHP ni Ruby.  
`laravel-patterns`, `laravel-plugin-discovery`, `laravel-security`, `laravel-tdd`, `laravel-verification`, `rails-patterns`

### Vue / Nuxt / Vite / Angular / Nest (6)

El front es Next, no Vue/Angular/Nest. El `5173` de CORS es residual, no un app Vite.  
`angular-developer`, `nestjs-patterns`, `nuxt4-patterns`, `ui-to-vue`, `vite-patterns`, `vue-patterns`

### Go / Rust / C# / C++ / Perl / F# / .NET (12)

Ninguno de esos lenguajes está en el árbol de aplicación.  
`cpp-coding-standards`, `cpp-testing`, `csharp-testing`, `dotnet-patterns`, `fsharp-testing`, `golang-patterns`, `golang-testing`, `perl-patterns`, `perl-security`, `perl-testing`, `rust-patterns`, `rust-testing`

### Video / motion / Remotion (11)

No hay pipeline de video.  
`blender-motion-state-inspection`, `fal-ai-media`, `frontend-slides`, `manim-video`, `motion-advanced`, `motion-foundations`, `motion-patterns`, `remotion-video-creation`, `tasteforge-video`, `video-editing`, `videodb`

### Homelab / Cisco / red de operador (10)

No se opera una red doméstica ni IOS.  
`cisco-ios-patterns`, `homelab-network-readiness`, `homelab-network-setup`, `homelab-pihole-dns`, `homelab-vlan-segmentation`, `homelab-wireguard-vpn`, `netmiko-ssh-automation`, `network-bgp-diagnostics`, `network-config-validation`, `network-interface-health`

### Healthcare clínico (4)

HIPAA ya se usó como lente; estas son de CDSS/EMR/PHI clínico.  
`healthcare-cdss-patterns`, `healthcare-emr-patterns`, `healthcare-eval-harness`, `healthcare-phi-compliance`

### DeFi / cripto / prediction markets (6)

No hay cadena ni mercado de predicción.  
`defi-amm-security`, `evm-token-decimals`, `llm-trading-agent-security`, `nodejs-keccak256`, `prediction-market-oracle-research`, `prediction-market-risk-review`

### Marca / marketing / inversor (11)

Piloto académico, no campaña ni deck.  
`brand-discovery`, `brand-voice`, `crosspost`, `growth-log`, `investor-materials`, `investor-outreach`, `lead-intelligence`, `market-research`, `marketing-campaign`, `social-graph-ranker`, `social-publisher`

### Agentes autónomos / harness LLM / ITO / ML de laboratorio (36)

Kawsay no es un orquestador de agentes ni un trainer. El RAG del producto ya se cubrió con `eval-harness` e `iterative-retrieval`.  
`agent-architecture-audit`, `agent-eval`, `agent-harness-construction`, `agent-introspection-debugging`, `agent-payment-x402`, `agent-self-evaluation`, `agent-sort`, `agentic-engineering`, `agentic-os`, `ai-first-engineering`, `autonomous-agent-harness`, `autonomous-loops`, `continuous-agent-loop`, `continuous-learning`, `continuous-learning-v2`, `council`, `council-multi-model`, `foundation-models-on-device`, `gan-style-harness`, `ito-baskets`, `ito-compute`, `ito-inference`, `ito-training`, `ml-adoption-playbook`, `mle-workflow`, `prompt-optimizer`, `pytorch-patterns`, `recsys-pipeline-architect`, `regex-vs-llm-structured-text`, `team-agent-orchestration`, `team-builder`, `enterprise-agent-ops`, `operator-approval-loop`, `openclaw-persona-forge`, `nasiko-control-plane`, `nanoclaw-repl`

### Orquestación de *implementación* ECC (6)

Excluidas por el plan: no se usa ECC para construir o parchear.  
`orch-add-feature`, `orch-build-mvp`, `orch-change-feature`, `orch-fix-defect`, `orch-pipeline`, `orch-refine-code`

### Ops de empresa / billing / logística / energy (12)

No es el dominio del piloto.  
`carrier-relationship-management`, `customer-billing-ops`, `customs-trade-compliance`, `energy-procurement`, `finance-billing-ops`, `inventory-demand-planning`, `logistics-exception-management`, `production-scheduling`, `quality-nonconformance`, `returns-reverse-logistics`, `counterparty-channel-discipline`, `connections-optimizer`

### Ciencia / literatura / USPTO / PubMed (5)

No hay pipeline científico.  
`scientific-db-pubmed-database`, `scientific-db-uspto-database`, `scientific-pkg-gget`, `scientific-thinking-literature-review`, `scientific-thinking-scholar-evaluation`

### Meta ECC extra / gusto / workflows de agente (18)

No hacen falta para juzgar este código.  
`configure-ecc`, `ecc-tools-cost-audit`, `skill-scout`, `hookify-rules`, `rules-distill`, `taste`, `taste-application`, `taste-distillation`, `santa-method`, `strategic-compact`, `inherit-legacy-style`, `intent-driven-development`, `loop-design-check`, `plan-canvas`, `ralphinho-rfc-pipeline`, `dynamic-workflow-mode`, `dmux-workflows`, `claude-devfleet`

### Runtimes / desktop / instaladores (7)

No hay app Windows nativa ni Bun/Flox como runtime del producto.  
`bun-runtime`, `flox-environments`, `generating-python-installer`, `uncloud`, `windows-desktop-e2e`, `unified-memory`, `tinystruct-patterns`

### Datos / search / scrapers / warehouses (8)

El almacén es MariaDB; no hay ClickHouse ni Prisma.  
`clickhouse-io`, `data-scraper-agent`, `data-throughput-accelerator`, `exa-search`, `prisma-patterns`, `ck`, `dashboard-builder`, `codehealth-mcp`

### Contenido, research ops, docs genéricos, demos (12)

No son el criterio de estado de Kawsay.  
`article-writing`, `content-engine`, `deep-research`, `knowledge-ops`, `research-ops`, `repo-scan`, `ui-demo`, `liquid-glass-design`, `master-agreement-generator`, `visa-doc-translate`, `esign-field-placement`, `nutrient-document-processing`

### SaaS colaterales / mail / Jira / Workspace / X (12)

No hay esos conectores en el producto (el envío real de SMS/correo está declarado pendiente en el README).  
`email-ops`, `google-workspace-ops`, `jira-integration`, `mailtrap-email-integration`, `messages-ops`, `unified-notifications-ops`, `x-api`, `mcp-server-patterns`, `api-connector-builder`, `hermes-imports`, `canary-watch`, `opensource-pipeline`

### Benchmarks, costo, competidores, equipos (11)

Útiles para otra conversación, no para el estado del árbol.  
`benchmark`, `benchmark-methodology`, `benchmark-optimization-loop`, `cost-tracking`, `competitive-platform-analysis`, `competitive-report-structure`, `automation-audit-ops`, `dev-team`, `terminal-opener`, `terminal-ops`, `latency-critical-systems`

**Comprobación del apéndice:** 5+10+10+5+6+6+12+11+10+4+6+11+36+6+12+5+18+7+8+12+12+11 = **223**.
