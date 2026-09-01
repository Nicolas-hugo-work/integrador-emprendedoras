# Kawsay — PWA de autonomía económica femenina

**Versión actual:** `v0.1.0`

Aplicación web progresiva para acompañar a emprendedoras bolivianas en el registro de su negocio, el control financiero, la orientación con fuentes verificadas y el ejercicio de sus derechos de privacidad.

No es solamente una base de datos. El proyecto incluye:

- una PWA responsive en Next.js, instalable desde un navegador compatible;
- una API en FastAPI con autenticación, verificación de contacto y roles configurables;
- MariaDB 11.8 con 62 tablas, índices convencionales, `FULLTEXT` y vectoriales;
- emprendimientos, movimientos financieros, costos y cálculo de precios;
- asistente RAG seguro que cita fuentes publicadas o se abstiene;
- consentimientos versionados, exportación, eliminación programada y auditoría;
- migraciones Alembic, tareas de purga, pruebas y contenedores Docker.

## Inicio rápido con Docker

Requisitos: Docker Desktop abierto y con el motor iniciado.

Desde PowerShell, en esta carpeta:

```powershell
docker compose up --build -d
```

Luego abre:

- aplicación: `http://localhost:3000`
- documentación interactiva de la API: `http://localhost:8000/docs`
- comprobación de salud: `http://localhost:8000/health`

También puedes hacer doble clic secundario y ejecutar con PowerShell [iniciar.ps1](C:/proyecto-integrador/iniciar.ps1). Para detener únicamente los servicios usa [detener.ps1](C:/proyecto-integrador/detener.ps1).

## Primer recorrido

1. Entra en `/registro` y crea una cuenta con una contraseña de 12 o más caracteres.
2. En desarrollo, el contacto se verifica automáticamente.
3. Registra el emprendimiento en **Mi negocio**.
4. Añade ingresos, gastos o costos desde **Finanzas**.
5. Usa **Asistente**. Si aún no hay fuentes publicadas, se abstendrá de forma segura.
6. Configura audio e investigación o solicita una copia desde **Privacidad**.

## Desarrollo sin contenedores

Base de datos:

```powershell
docker compose up -d mariadb
```

Backend:

```powershell
cd C:\proyecto-integrador\backend
Copy-Item .env.example .env
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Frontend, en otra terminal:

```powershell
cd C:\proyecto-integrador\frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

## Roles administrativos y fuentes RAG

Las cuentas nuevas reciben `EMPRENDEDORA`. Para convertir una cuenta local en curadora de fuentes:

```powershell
cd C:\proyecto-integrador\backend
.\.venv\Scripts\python.exe scripts\assign_role.py correo@ejemplo.com CURADORA_RAG
```

La curadora puede crear una fuente, agregar una versión y fragmentos, y publicarla mediante la documentación en `/docs`. Solo las versiones publicadas intervienen en respuestas nuevas.

## Pruebas

```powershell
cd C:\proyecto-integrador\backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check app tests scripts

cd C:\proyecto-integrador\frontend
npm run lint
npm run build
```

La prueba de migración real requiere que MariaDB esté disponible. Puede ejecutarse así:

```powershell
$env:TEST_DATABASE_URL='mysql+pymysql://pwa_app:change_me_local@localhost:3306/pwa_autonomia?charset=utf8mb4'
cd C:\proyecto-integrador\backend
.\.venv\Scripts\python.exe -m pytest tests\test_mariadb_integration.py
```

## Estructura

```text
C:\proyecto-integrador
├── frontend       PWA Next.js y pantallas
├── backend        API, modelos, migraciones, pruebas y documentación
├── docker-compose.yml
├── iniciar.ps1
└── detener.ps1
```

La descripción de dominios, relaciones, retención y diccionario resumido está en [architecture.md](C:/proyecto-integrador/backend/docs/architecture.md).

## Límites actuales del MVP

- El asistente actual es de recuperación segura: extrae evidencia publicada, pero no conecta todavía un proveedor externo de modelo generativo.
- La transcripción de voz y el envío real de códigos por SMS/correo requieren elegir proveedores.
- La exportación de datos crea la solicitud; un trabajo posterior debe generar y entregar el archivo.
- Antes de producción deben reemplazarse todos los secretos locales, habilitar HTTPS, almacenamiento de objetos y copias de respaldo verificadas.
