# ADR 001 — Esquema que sigue dormido

**Estado:** aceptado (v0.12.0)

Tres piezas del esquema inicial **no** autorizan ni tienen HTTP. Quedan
reservadas a propósito.

## `business_memberships`

Se escribe un OWNER al crear el emprendimiento. El acceso real usa
`owned_business` (dueña = `owner_user_id`). Despertar memberships para finanzas
grupales reescribe esa frontera. No se activa hasta una versión que lo declare
y lo mida.

## `organizations` / `organization_memberships`

Preparación institucional. Sin interfaz. Una ONG o municipio no entra por esta
puerta todavía.

## `background_jobs`

El worker de Compose ejecuta `python -m app.tasks` cada hora. No hace falta
despertar la tabla para programar purgas.

## Consecuencia

Nadie «activa» grupales ni un bus de jobs sobre el código de 0.12. Si hace
falta, es otra MINOR con contrato, pruebas de acceso horizontal y CHANGELOG.
