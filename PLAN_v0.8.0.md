# Kawsay v0.8.0 — Que funcione sin conexión, y que cuando no pueda, lo diga

> **Estado:** entregado en `main` (v0.8.0).
> **Versión anterior:** v0.7.0 (banco de evaluación y recuperación `FULLTEXT`).
> **Alcance:** enteramente de cliente. Sin cambios de esquema, sin migración y
> sin una sola operación nueva en la API.

## Contexto

El `README.md` llama PWA a Kawsay y el público declarado son mujeres
emprendedoras en Bolivia con conectividad intermitente. Hoy eso no se cumple, y
lo verifiqué leyendo el código:

- **El service worker no cachea nada.** `frontend/public/sw.js` precachea tres
  URLs en `install` y su manejador de `fetch` **no tiene un solo `cache.put`**.
  El caché contiene esas tres entradas para siempre. Sin red, el HTML de `/` se
  sirve, pero sus `/_next/static/*.js` y `*.css` no están cacheados, caen al
  fallback, reciben el HTML de `/`, y `X-Content-Type-Options: nosniff`
  (`next.config.ts:9`) los bloquea. Queda una página sin estilos ni JavaScript.

- **Y falla en silencio mintiendo.** `frontend/app/page.tsx:64` es
  `.catch(() => undefined)`. Sin red, la primera pantalla que ve la usuaria
  muestra **«Tu saldo registrado es Bs 0,00»** con total confianza, porque
  `summary` se queda en los ceros con que se inicializó (`page.tsx:34-38`). Un
  saldo falso es peor que un error: parece verdadero.

- **El error de red le llega en inglés.** `api.ts:11` define
  `GENERIC_ERROR = 'No se pudo completar la solicitud.'` pero solo se usa en
  `toError` (`api.ts:85`), para respuestas HTTP. Un `fetch` que rechaza por red
  nunca pasa por ahí, así que `describe(reason)` muestra el
  `TypeError: Failed to fetch` del navegador.

- **Se puede enviar dos veces.** Los botones de guardar de `/finanzas`
  (`finanzas/page.tsx:329`) y `/emprendimiento` (`emprendimiento/page.tsx:187`)
  no se deshabilitan ni muestran pendiente. En 2G no hay reacción visible, y
  `POST /finance/movements` no es idempotente.

**Resultado buscado:** que sin conexión la aplicación degrade en vez de
romperse, y que nunca presente como cierto un dato que no pudo comprobar.

## Lo que verifiqué antes de escribir esto

- **`next/offline` existe en este build**: `node_modules/next/offline.js`
  reexporta `dist/client/components/use-offline`. Requiere
  `experimental.useOffline` en `next.config.ts`, que hoy **no tiene bloque
  `experimental` en absoluto**.
- **Matiz decisivo, de la doc local** (`docs/01-app/02-guides/offline-support.md`):
  - Línea 21: *"Requests you issue directly with `fetch()` inside a Client
    Component […] stay under that library's own retry policy."* Kawsay es
    enteramente eso, así que **la bandera no reintenta las peticiones de datos**.
    Da la señal de conectividad fiable y reintenta navegaciones.
  - Línea 139: *"A full page reload while offline still fails […] full offline
    loads would need a service worker."* La bandera **no sustituye** al SW.
  - Línea 423: *"Test this feature with `next build && next start`. Dev mode is
    not a reliable reference."*
- **`sharp` está en `node_modules`**, así que los iconos PNG del manifiesto se
  pueden generar desde `public/favicon.svg` sin añadir dependencias.
- **El manifiesto actual no es instalable**: `public/manifest.webmanifest:10`
  declara un solo icono SVG con `sizes: "any"`; la guía PWA local pide PNG de
  192 y 512.

---

## Fase 0 — La deuda que miente

Primero y en su propio commit, para que el resto del diff quede limpio. Solo
entra aquí lo que hoy **afirma algo falso**.

| Qué | Dónde | Qué dice hoy |
|---|---|---|
| Versión desincronizada | `VERSION` | `0.6.0`, mientras `backend/pyproject.toml:7`, `backend/app/main.py:50` y `frontend/package.json:3` dicen `0.7.0` |
| README congelado | `README.md:3` | *"Versión actual: v0.1.0"*; y `README.md:118` declara la exportación como no entregada, cuando se entregó en v0.4.0 |
| Siembra obsoleta | `backend/sql/seeds.sql:9-19` | Siembra los 10 permisos de `0001` y **le falta `business.manage_own`**, añadido por `0002`. Nadie la ejecuta hoy (solo la lee `scripts/export_schema.py:57`), pero una base creada desde ahí dejaría a toda emprendedora sin sus propios emprendimientos |
| Promesas vencidas | `backend/app/domain_rules.py:60-67`, `backend/app/services/rate_limit.py:6-11` | Prometen cosas *"para v0.3.0"*; estamos en v0.8.0. Se corrige el texto para que diga lo que es verdad, no se cambia el comportamiento |
| Docstring falso | `backend/app/domain_rules.py:76-84` | Dice que `optional_feature_allowed` *"no tiene todavía punto de uso"*; se usa en `privacy_service.py:56` desde v0.3.0 |
| Nota de desarrollo en producción | `frontend/app/registro/page.tsx:73` | Le muestra a la usuaria final *"En el entorno local la verificación se completa automáticamente"* |
| Botón muerto | `frontend/app/page.tsx:342-344` | *"Continuar diagnóstico"* es un `<button>` sin `onClick`. Las tablas de diagnóstico duermen sin endpoint; se retira el botón |
| Recuento engañoso | `frontend/app/page.tsx:196` | Dice `${movements.length} movimientos recientes` después de un `.slice(0, 3)`: nunca dirá más de 3 |
| Fuente que nadie usa | `frontend/app/layout.tsx:2,7-10` | Descarga `Geist_Mono` (parte de 168 KB de `.woff2`) y `font-mono` no aparece en ninguna pantalla |
| Lock desincronizado | `frontend/package-lock.json:3` | `0.1.0` desde siempre |

**Peso muerto del repositorio, en commit aparte y reversible solo:**
`frontend/components/ui/` (60 componentes shadcn, 351 KB, excluidos en
`tsconfig.json:44-48` y sin un solo import desde `app/`), `frontend/vite.config.ts`
(configuración de Vite + Cloudflare de otro generador), `components.json`, y los
`hooks/`/`lib/` sueltos de la raíz del frontend.

> Es lo único irreversible del plan. No cuesta ancho de banda a nadie —nunca
> entra al bundle—, solo bytes de repositorio. Va en su propio commit para que
> revertirlo no toque nada más. Si prefieres conservarlo, se cae este commit y
> el resto de la versión queda igual.

---

## Fase 1 — Un service worker que de verdad cachea

Reescritura de `frontend/public/sw.js` (hoy 17 líneas):

- **Cache-first para `/_next/static/**`.** Son inmutables y llevan hash en el
  nombre, así que guardarlos al vuelo con `cache.put` es seguro por
  construcción: una versión nueva pide nombres nuevos y nunca se sirve una
  mezcla. Esto es exactamente lo que hoy falta.
- **Network-first para documentos**, guardando la respuesta buena; si no hay
  red, la copia cacheada; si tampoco, `/offline`.
- **Se mantiene el filtro por origen** (`sw.js:15`): las llamadas a la API no
  pasan por el SW. Es correcto y deliberado: nunca se sirven datos rancios sin
  decirlo, de eso se encarga la Fase 3.
- Caché versionado (`kawsay-shell-v2`); la limpieza de los viejos en `activate`
  ya existe y se conserva.

Pantalla nueva `frontend/app/offline/page.tsx`: estática, sin datos, explica que
no hay conexión y qué sí se puede seguir viendo.

---

## Fase 2 — Decir la verdad sobre la conexión

- `frontend/next.config.ts`: añadir `experimental: { useOffline: true }`,
  conservando intactas las cabeceras que ya tiene.
- `frontend/app/components/offline-banner.tsx` (nuevo): cliente, usa
  `useOffline()` de `next/offline`, con `role="status"` para que un lector de
  pantalla lo anuncie. No pinta nada cuando hay conexión.
- Va en `frontend/app/layout.tsx`, no en `AppShell`: `app/page.tsx` reimplementa
  la barra lateral entera en vez de usar `AppShell`, así que solo desde el
  layout cubre las dos.

**Por qué la bandera no basta, y hay que decirlo en el CHANGELOG:** reintenta
navegaciones, prefetch y Server Actions. Los datos de Kawsay los pide
`api.ts` con `fetch()` desde componentes cliente, que la doc excluye
explícitamente. Lo que ganamos aquí es la *detección* fiable —mejor que
`navigator.onLine`, que devuelve `true` en un portal cautivo—; el
comportamiento de los datos es la fase siguiente.

---

## Fase 3 — Última sincronización en vez de un cero falso

Es la parte sustantiva y la que arregla el defecto de confianza.

**`frontend/app/lib/offline-cache.ts`** (nuevo): guarda en IndexedDB la última
respuesta buena de cada GET con su marca de tiempo. Se elige IndexedDB y no
`localStorage` porque son respuestas JSON completas y porque hoy el proyecto no
usa ninguna de las dos (solo `sessionStorage` para los dos tokens,
`api.ts:8-9`). Se limpia al cerrar sesión, junto a `clearTokens()`.

**`frontend/app/lib/api.ts`**: se añade

```ts
apiCached<T>(path): Promise<{ data: T; fetchedAt: Date | null; stale: boolean }>
```

`api()` conserva su firma exacta —la llaman más de cuarenta sitios— y sigue
lanzando. `apiCached` guarda las respuestas buenas y, ante un fallo **de red**
(no HTTP), devuelve la copia con `stale: true`. Además, `api()` envuelve el
fallo de red en un `Error` con texto propio en español, para que
`describe(reason)` deje de mostrar el `TypeError` del navegador.

**`frontend/app/lib/staleness.ts`** (nuevo, puro): `describeStaleness(fetchedAt,
now)` → «actualizado hace 3 horas», «hace 2 días». Función pura a propósito: es
la parte verificable con Vitest, que es como el proyecto prueba el frontend.

**El cero falso, arreglado.** `frontend/app/page.tsx` y
`frontend/app/finanzas/page.tsx` pasan a tres estados honestos:

1. cargando (con `aria-live`, porque hoy los nueve spinners son mudos para un
   lector de pantalla),
2. datos, con su antigüedad visible si vienen del caché,
3. no se pudo cargar, dicho como tal.

Ninguno de los tres muestra `Bs 0,00` sin saber que es cierto.

---

## Fase 4 — Que no se pierda ni se duplique lo que se escribe

- Botones de guardar con `disabled` e indicador de pendiente en
  `frontend/app/finanzas/page.tsx:329` y
  `frontend/app/emprendimiento/page.tsx:187`. Hoy ninguno de los dos toca un
  estado de carga; `emprendimiento/page.tsx` no contiene la palabra `disabled`.
- **Las escrituras sin conexión se rechazan con un mensaje claro**, no se
  encolan: «no se guardó porque no hay conexión; vuelve a intentarlo cuando
  vuelva». Encolar escrituras que no son idempotentes es un problema de
  duplicados y de orden que merece su propia versión, y decir «guardado» sobre
  algo que quizá nunca llegue sería repetir el error del saldo falso en otro
  sitio.

---

## Fase 5 — Que se pueda instalar

- `frontend/app/manifest.ts` (convención de Next 16) sustituye a
  `public/manifest.webmanifest`, con PNG de 192 y 512, `purpose: "maskable"`,
  `id`, `scope` y `background_color`.
- Los dos PNG se generan una vez desde `public/favicon.svg` con `sharp`, que ya
  está en `node_modules`, y se commitean.
- `frontend/app/pwa-register.tsx` (hoy 11 líneas de registrar y olvidar, con
  `.catch(() => undefined)`) pasa a detectar `updatefound` y avisar de que hay
  una versión nueva.

---

## Fase 6 — Cierre

- Vitest sobre lo puro: `describeStaleness`, qué decide cachearse y qué no, y el
  texto del error de red.
- Prueba en el backend que lee los **cinco** lugares de versión (`VERSION`,
  `backend/pyproject.toml`, `backend/app/main.py`, `frontend/package.json`,
  `frontend/package-lock.json`) y exige que coincidan. Es lo que habría
  detectado que `VERSION` se quedó en 0.6.0.
- Sección nueva en `PRUEBAS_POR_ROL.txt` con la prueba manual sin conexión,
  advirtiendo que hay que hacerla con `next build && next start` porque la doc
  dice que el modo desarrollo no es referencia fiable.
- Versiones a `0.8.0` en los cinco lugares, `CHANGELOG.md`, PR y etiqueta tras
  CI en verde.

---

## Lo que NO entra

- **Cola de escrituras sin conexión.** Fase 4 explica por qué.
- **Búsqueda vectorial y modelo generativo.** Siguen siendo la decisión que el
  proyecto aplaza a propósito desde v0.2.0.
- **Quechua y aymara.** No hay ningún mecanismo de i18n y las ~4.600 líneas de
  `app/` tienen las cadenas escritas directamente en el JSX. `User.locale` llega
  del backend y el frontend no lo lee nunca. Es una versión entera, no un
  apartado de esta.
- **Accesibilidad a fondo.** Entra solo lo que es del tema —el banner y los
  estados de carga anunciados—. Quedan anotados y sin tocar: el cajón de
  navegación sigue siendo enfocable con el menú cerrado
  (`app-shell.tsx:32-34`), `role="alert"` está en 4 de 9 pantallas, y no hay
  enlace de salto al contenido.
- **Que `app/page.tsx` deje de duplicar `AppShell`.** Es la causa de las
  divergencias entre ambas barras, pero es un refactor de 350 líneas con riesgo
  de regresión visual y no hace falta para nada de esta versión.
- **Que las purgas de `tasks.py` corran de verdad.** Lo encontré y es real
  —nadie lo programa, así que la eliminación de cuenta que prometemos no
  ocurre—, pero es backend y es otro tema. Candidato fuerte para la v0.9.0.

---

## Verificación

```bash
cd frontend
npm run lint          # oxlint + tsc
npm run test          # Vitest
npm run build
npm start             # obligatorio: la doc dice que dev no sirve para probar offline

cd ../backend
export TEST_DATABASE_URL="mysql+pymysql://pwa_app:change_me_local@127.0.0.1:3306/kawsay_test?charset=utf8mb4"
export TEST_MIGRATION_DATABASE_URL="mysql+pymysql://pwa_app:change_me_local@127.0.0.1:3306/kawsay_migration?charset=utf8mb4"
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/ruff.exe check app tests alembic scripts
```

**Prueba manual sin conexión** (Chrome, DevTools → Network → Offline), contra
`npm start`, no contra `npm run dev`:

- [ ] Con red, visitar `/` y `/finanzas`. Cortar la red y **recargar**: la
      aplicación carga, con estilos y con JavaScript. Hoy aquí sale una página
      cruda sin estilos.
- [ ] Sin red, `/` muestra los últimos datos conocidos con su antigüedad, o dice
      que no pudo cargar. **Nunca `Bs 0,00` sin respaldo.**
- [ ] El banner de sin conexión aparece y se anuncia; desaparece al volver la
      red.
- [ ] Sin red, guardar un movimiento dice que no se guardó. Al volver la red,
      guardarlo funciona y **no aparece duplicado**.
- [ ] Tocar dos veces «Guardar» con red lenta crea **un** movimiento, no dos.
- [ ] Una ruta nunca visitada, sin red, lleva a `/offline`, no a un error del
      navegador.
- [ ] En Chrome Android (o DevTools → Application → Manifest) la aplicación
      ofrece instalarse.

**Criterios de aceptación**

- [ ] `sw.js` escribe en caché: tras una visita con red, `/_next/static/*` está
      en el caché del navegador.
- [ ] Ninguna pantalla presenta un dato numérico que no pudo comprobar.
- [ ] Un fallo de red produce un mensaje en español, no un `TypeError`.
- [ ] Los cinco lugares de versión coinciden, y hay una prueba que lo exige.
- [ ] El diff de OpenAPI es **vacío**: esta versión no toca la API.
- [ ] `alembic check` limpio y huella de `information_schema` sin cambios.
- [ ] CI en verde en los tres trabajos.

---

## Riesgos

| Riesgo | Medida |
|---|---|
| `experimental.useOffline` es experimental y puede cambiar | Se usa solo para *leer* el estado en un banner. Si la bandera desapareciera, se cae el banner y nada más; el SW y el caché de datos no dependen de ella |
| Un service worker mal hecho sirve una versión vieja para siempre | Documentos en network-first (nunca se sirve HTML viejo habiendo red) y estáticos con hash en el nombre (imposible mezclar versiones). `Cache-Control: no-store` sobre `/sw.js` ya está en `next.config.ts:19` |
| CI no puede probar comportamiento offline fácilmente | La lógica pura va a Vitest; el comportamiento del navegador va a la prueba manual, escrita y versionada en `PRUEBAS_POR_ROL.txt` |
| Mostrar datos viejos confunde | Nunca se muestran sin su antigüedad al lado. Es justamente lo contrario del defecto que arregla la versión |
| Borrar `components/ui/` elimina trabajo existente | Va en su propio commit, revertible solo, y es el único paso irreversible del plan |
| La versión crece de más | La cola de escrituras, la i18n y la accesibilidad a fondo quedan fuera explícitamente |
