# Historial de versiones

Este proyecto utiliza [versionado semántico](https://semver.org/lang/es/):

- `PATCH` (`0.1.1`): correcciones sin funciones nuevas.
- `MINOR` (`0.2.0`): nuevas funciones compatibles.
- `MAJOR` (`1.0.0`): versión estable o cambios incompatibles.

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
