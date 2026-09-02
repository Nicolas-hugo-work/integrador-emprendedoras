# Historial de versiones

Este proyecto utiliza [versionado semántico](https://semver.org/lang/es/):

- `PATCH` (`0.1.1`): correcciones sin funciones nuevas.
- `MINOR` (`0.2.0`): nuevas funciones compatibles.
- `MAJOR` (`1.0.0`): versión estable o cambios incompatibles.

## [0.7.0] - 2026-09-02

Primero medir, despues mejorar. El asistente es la funcion mas visible del
proyecto y hasta ahora no habia forma de saber si un cambio lo mejoraba o lo
empeoraba. Esta version construye el banco de evaluacion, cambia la recuperacion
y **mide el cambio** en vez de afirmarlo.

### Banco de evaluacion

- Siete operaciones nuevas bajo `/evaluation` (49 -> 56), sobre las cuatro
  tablas que el esquema inicial traia dormidas: `evaluation_sets`,
  `evaluation_cases`, `evaluation_runs` y `evaluation_results`. **Sin cambios de
  esquema y sin migracion.**
- Que se le exige a una respuesta lo decide la `category` del caso, que ya era
  una taxonomia cerrada en la base. Quien redacta un caso no puede inventarse
  una expectativa que nadie sabe verificar.
- `assistant_service.evaluate_message` separa calcular la respuesta de guardar
  la conversacion. El banco recorre **el mismo camino** que atiende a las
  usuarias, no una copia que divergiria en silencio; hay una prueba de que las
  dos dan la misma respuesta.
- Ejecutar una tanda no crea conversaciones, mensajes ni `AIRun`. Tambien hay
  prueba de eso: evaluar no debe ensuciar las conversaciones de nadie.
- Leer el banco lo puede la curaduria **o** la auditoria. Para expresarlo,
  `authorization.py` gana `assert_any_permission`: hasta ahora toda ruta exigia
  un permiso unico. La auditora lee y compara, pero no ejecuta.
- `INJECTION` y `PII` hoy pasan por construccion, porque sin generacion el
  sistema no puede desviarse ni inventar. Se vigilan igual: el dia que se agregue
  un modelo generativo esas garantias dejan de ser gratis, y ese es el dia en que
  el banco tiene que avisar.

### Recuperacion: de `LIKE` a `FULLTEXT`

`_retrieve_published` pasa a usar `idx_source_chunks_fulltext`, creado en la
migracion `0001` y **nunca usado hasta hoy**. Tres cosas que antes no existian:

- **Orden por relevancia.** Antes tomaba los tres primeros que encontrara, en el
  orden que devolviera la base.
- **Coincidencia por palabra completa**, no por subcadena.
- **Descarte de palabras vacias**, en vez de buscar «para» o «necesito».

Ademas, una consulta sin ninguna palabra utilizable ahora se abstiene. Antes
devolvia tres fragmentos cualesquiera: citar algo que no viene al caso enganna
mas que decir que no se sabe.

`AIRun.model_version` pasa de `v1` a `v2`, para que cada corrida quede atribuida
a la implementacion que la produjo. **Esto cambia lo que el asistente responde**,
a proposito.

### La medicion

Sobre el conjunto sembrado por `scripts/seed_evaluation_set.py` —ocho documentos
con vocabulario compartido, diez casos de las siete categorias—, la misma tanda
corrida con las dos recuperaciones:

| Medida | v1 (`LIKE`) | v2 (`FULLTEXT`) |
|---|---|---|
| Casos que pasan | 90 % | 100 % |
| Recuperacion (recall) | 80 % | 100 % |
| Respuestas con cita | 80 % | 80 % |
| Con advertencia normativa | 50 % | 50 % |
| Abstenciones | 20 % | 20 % |

Dos casos cambiaron, los dos tributarios: con `LIKE` el asistente citaba los
documentos equivocados —los que compartian las palabras corrientes del
dominio— y en `SAFE-01` llegaba a advertir correctamente **citando otra cosa**.
Es una mejora modesta y medida sobre diez casos, no un salto; el valor de la
version es que ahora se puede afirmar cual es.

### Pantalla de evaluacion

- `/evaluacion`, visible para curaduria y auditoria. El enlace va despues de
  Curaduria, Administracion y Auditoria: ninguna de las dos empieza su trabajo
  aqui, y la navegacion decide donde aterriza cada rol.
- Conjuntos con sus casos y su categoria, boton para ejecutar, y **comparacion
  entre dos corridas**, que es el punto de todo esto.
- La navegacion admite enlaces que abre cualquiera de varios permisos, igual que
  `assert_any_permission` en el backend.

### Guiones

- `scripts/create_test_databases.py` recrea `kawsay_test` y `kawsay_migration`.
  La purga de Docker se las habia llevado, y reconstruirlas de memoria cada vez
  es tiempo perdido.
- `scripts/seed_evaluation_set.py` publica su propio corpus, con distractores
  que comparten vocabulario, para que la comparacion no dependa de lo que cada
  quien tenga cargado.
- `scripts/compare_retrieval.py` corre la misma tanda con las dos
  recuperaciones. Conserva el `LIKE` de `v0.1.0` como material de laboratorio:
  no vuelve a la aplicacion.

### Pruebas

- Backend 265 -> 302; frontend 35 -> 50. Ninguna omitida.
- Las pruebas RAG dejan de consultar con palabras corrientes. La base de prueba
  se conserva entre ejecuciones, asi que una consulta con «sobre» acababa
  recuperando el documento de otra prueba.
- El inventario de autorizacion admite rutas que abre cualquiera de varios
  permisos, y elige como intrusa a quien carece de **todos**.

## [0.6.0] - 2026-09-02

Cargar un documento en la curaduria pasa a ser pegar su texto una vez y revisar
como quedo partido. Antes habia que pegarlo dos veces: entero para la version, y
despues trozo por trozo en otro formulario.

### Carga de documentos

- `POST /source-versions/{id}/chunks` recibe la tanda completa de fragmentos y
  la inserta en **una sola transaccion**. Una peticion por fragmento dejaria,
  ante un fallo a media carga, una version publicable con el contenido
  incompleto: el asistente citaria un documento truncado sin que nadie lo note.
- El numero correlativo y el recuento de palabras los calcula el servidor.
- `source_chunks` tiene unicidad sobre `(version, hash del contenido)`, y en un
  documento normativo repetir un parrafo es frecuente. En vez de dejar que
  estalle una violacion de integridad, se comprueba antes y se dice **cuales**
  son los repetidos.

### Pantalla de curaduria

- Tres pasos numerados con su estado, en vez de tres formularios sueltos.
- El texto pegado se divide solo en fragmentos, con vista previa editable: se
  pueden unir con el anterior, separar en dos o descartar antes de guardar. Los
  duplicados exactos se descartan y se avisa cuantos.
- El enlace oficial acepta `www.seprec.gob.bo` sin `https://`: se completa solo.
- Se explica por que "Publicar" esta deshabilitado en lugar de dejarlo gris y
  mudo, y la ayuda deja de hablar de "huella SHA-256" para decir para que sirve.

### Sin cambios de esquema

Las 62 tablas, indices, vista y triggers siguen identicos a los de `0.1.0`.

## [0.5.0] - 2026-09-01

`ADMINISTRADORA` deja de tener una sola pantalla de solo lectura:
`account.suspend` pasa a ser un permiso con endpoints. La API va de 41 a 48
operaciones, sin cambios de esquema y sin migracion.

### El bloqueo por intentos deja rastro

- El limitador que introdujo `0.2.0` bloqueaba una cuenta en memoria y nadie se
  enteraba. Ahora escribe en `security_alerts`, tabla que existia desde el
  esquema inicial sin usarse.
- La alerta se crea **en la transicion** al bloqueo: cinco fallos generan una
  alerta, no cinco. Tampoco se duplica mientras siga abierta.
- La descripcion nunca lleva el contacto probado ni la contrasena. Un intento
  contra un contacto inexistente tambien deja alerta, con `user_id` nulo.

### Cola de alertas y acciones sobre cuentas

- `GET /security-alerts` exige `audit.read`: la auditora ve la cola igual que
  la administradora, pero recibe `403` al resolver o suspender. Leer es de
  auditoria; actuar, de administracion.
- `POST /security-alerts/{id}/acknowledge` y `/resolve`.
- `GET /accounts/lookup` busca por contacto **completo**: sin comodines, sin
  listados, y deja evento de auditoria con quien busco a quien.
- `GET /accounts/{id}` para llegar desde una alerta al estado y los roles.
- `POST /accounts/{id}/suspend` y `/reactivate`.

### Decisiones que conviene conocer

- `SecurityAlertView` **si** expone `user_id`, a diferencia del visor de
  auditoria. Es el unico punto donde se levanta la seudonimizacion, porque sin
  el no habria forma de llegar a una cuenta; la lectura de la cola se audita.
- Suspender revoca todas las sesiones y corta el acceso de inmediato.
- No se puede suspender la cuenta propia ni otra que tenga `account.suspend`:
  nadie puede dejar el sistema sin administracion.
- Solo se reactiva desde `SUSPENDED`; una cuenta eliminada no vuelve por esta
  via porque su purga ya esta programada.
- El motivo de una suspension queda en `metadata_json` del evento de
  auditoria, columna que existia sin uso, y entra en su hash de integridad.

### Sin cambios de esquema

Las 62 tablas, indices, vista y triggers siguen identicos a los de `0.1.0`.

## [0.4.0] - 2026-09-01

Los roles dejan de ser decorativos: cada uno accede solo a sus funciones. La
API pasa de 39 a 41 operaciones y 19 endpoints existentes empiezan a exigir
permiso.

### El rol ahora significa algo

- Los endpoints de emprendimientos, finanzas y conversaciones exigen sus
  permisos (`business.manage_own`, `finance.read_own`, `finance.write_own`,
  `conversation.manage_own`). Antes autorizaban solo por propiedad, asi que una
  cuenta con solo `CURADORA_RAG` creaba emprendimientos y leia finanzas.
- `/me`, `/consents` y `/privacy/*` quedan **fuera** del gateo: son derechos de
  toda cuenta. Una curadora sigue pudiendo retirar consentimientos, descargar
  sus datos y borrar su cuenta.
- El login lleva a la primera pantalla que la usuaria puede abrir, en vez de al
  panel de emprendedora fijo.

### Migraciones de verdad

- `alembic check` funciona por primera vez y es un paso de CI: detecta si un
  modelo cambia sin su migracion. Antes reventaba al reflejar la columna
  `VECTOR(768)`.
- `0002_business_permission` es la primera migracion real, y siembra el permiso
  que faltaba para `/businesses`.
- Ninguna revision posterior a la inicial puede usar `create_all`, y todas
  deben ser reversibles.

### Auditoria e investigacion

- `GET /audit-events` con filtros y paginado, y pantalla propia. Es el primer
  uso de `audit.read`, el permiso que comparten `ADMINISTRADORA` y
  `AUDITORA_INVESTIGADORA`. Nunca devuelve el identificador real de quien
  actuo, solo su seudonimo.

### Exportacion de datos

- `GET /privacy/export/{id}` genera la copia en el momento y la descarga.
  `POST /privacy/export` registraba una solicitud que nadie cumplia nunca.
- La seleccion es una lista blanca, y una prueba comprueba que ninguna tabla
  que la purga borra quede olvidada por la exportacion.

### Sin cambios de esquema

Las 62 tablas, indices, vista y triggers siguen identicos a los de `0.1.0`.

## [0.3.0] - 2026-09-01

Cierra tres promesas que la aplicacion no cumplia: no se podia corregir un
error, la curaduria de fuentes no era alcanzable desde el producto, y la
pantalla de privacidad mostraba un estado que no era el guardado. La API pasa
de 26 a 39 operaciones, todas aditivas: ninguna operacion previa cambio.

### Se puede corregir

- `PATCH` y `DELETE` sobre movimientos, costos y emprendimientos. Hasta ahora
  la API tenia 19 `POST`, 7 `GET` y ningun verbo de mutacion, asi que un monto
  mal tipeado era permanente.
- `GET /finance/costs`, para poder ver los costos y corregirlos.
- Borrar un emprendimiento no borra su historial financiero, y borrar un costo
  no altera escenarios de precio ya calculados.

### Curaduria alcanzable

- `GET /source-publishers`, `GET /sources`, `GET /sources/{id}/versions` y
  `GET /source-versions/{id}/chunks`.
- `POST /source-versions/{id}/retire`: la contraparte que faltaba de publicar.
  Sacar de circulacion una norma desactualizada exigia un `UPDATE` manual.
- Publicar y retirar quedan registrados en `source_status_history`, con quien
  hizo el cambio y por que. La tabla existia sin usarse desde el esquema
  inicial.
- Pantalla `/curaduria`, visible solo con el permiso `source.review`.

### Privacidad honesta

- `GET /consents` devuelve la decision vigente por finalidad, junto con lo que
  implica retirarla. La pantalla deja de mantener el estado solo en el cliente:
  al recargar ya muestra lo que quedo guardado.

### Autorizacion

- `/me` devuelve `roles` y `permissions`, de modo que la interfaz se condiciona
  por capacidad con los mismos codigos que verifica el backend.
- Nuevo inventario de autorizacion: cada operacion debe declararse como
  publica, autenticada o exigente de un permiso, y una ruta sin clasificar hace
  fallar la bateria. En v0.1.0 se sembraron 10 permisos y solo 2 llegaban a
  verificarse.
- La comprobacion de contrato pasa de exigir identidad a exigir compatibilidad
  hacia atras: las operaciones previas no pueden cambiar y las nuevas deben
  declararse.

### Sin cambios de esquema

Las 62 tablas, indices, vista y triggers son identicos a los de `0.1.0`. Toda
la funcionalidad se apoya en columnas que ya existian.

## [0.2.0] - 2026-09-01

Refactor estructural del backend, endurecimiento de la autenticación y
primera integración continua. La superficie HTTP se conserva: las mismas 26
operaciones, rutas, códigos, schemas y textos de error, verificado contra un
snapshot de OpenAPI de `0.1.0`.

### Cambios de comportamiento

- `/auth/register` ya no responde `409` cuando el contacto está registrado.
  Devuelve la misma respuesta que un alta nueva, sin crear nada, para que no
  sea posible enumerar cuentas. Quien reintente el registro con su propia
  contraseña seguirá pudiendo iniciar sesión; quien la ignore recibirá
  `Credenciales inválidas`.
- `/auth/login` y `/auth/verify-contact` responden `429` tras varios intentos
  fallidos, con una espera que se duplica en cada exceso.
- La aplicación se niega a arrancar si `JWT_SECRET` o
  `CONTENT_ENCRYPTION_KEY` conservan el valor de ejemplo del repositorio, o
  miden menos de 32 caracteres, con `APP_ENV` distinto de `development`.
- `/assistant/query` deja de fallar con `500` cuando dos consultas
  simultáneas sobre la misma conversación colisionan al numerar mensajes.
- El frontend renueva el token de acceso de forma transparente ante un `401`
  en lugar de expulsar a la usuaria a los 15 minutos.

### Arquitectura

- `main.py` pasa de 733 a 49 líneas: solo compone la aplicación y registra
  routers. Los endpoints viven en `app/routers/` y los casos de uso en
  `app/services/`, con las reglas de capas verificadas por pruebas.
- Excepciones de aplicación independientes de FastAPI, traducidas a HTTP por
  un único manejador.
- Un solo `utc_now()`; se elimina `datetime.utcnow()`, obsoleto desde 3.12.

### Calidad

- Integración continua con MariaDB 11.8 real. Antes no existía ninguna, y la
  única prueba que tocaba la base se saltaba siempre en silencio.
- Snapshot de OpenAPI y huella de `information_schema` como pruebas de
  regresión de contrato y de esquema.
- Baterías nuevas: recorrido completo, aislamiento entre usuarias, RAG,
  privacidad, endurecimiento y reglas de arquitectura.
- `npm run lint` pasa a ejecutar `oxlint` además de `tsc`; se añade Vitest
  para el cliente HTTP.

## [0.1.0] - 2026-09-01

### Incluye

- PWA responsive en Next.js para emprendedoras.
- API FastAPI con autenticación, verificación y RBAC.
- Gestión de emprendimientos y libro financiero simple.
- Asistente RAG con citas y abstención segura.
- Consentimientos, exportación y eliminación programada.
- Esquema MariaDB de 62 tablas con migraciones Alembic.
- Contenedores Docker, pruebas automatizadas y documentación técnica.
