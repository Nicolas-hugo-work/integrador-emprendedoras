# Seguridad

Si encontrás una vulnerabilidad en Kawsay, no abras un issue público.

Escribí a quienes mantienen el repositorio por un canal privado (correo o
mensaje directo en GitHub) y esperá confirmación antes de divulgar.

## Qué no reportar aquí

Secretos de laboratorio en `docker-compose.yml` (`change_me_local`) son
marcadores de desarrollo. Un despliegue real debe cambiarlos; `APP_ENV` distinto
de `development` rechaza los valores de ejemplo.

## Superficie actual

- El refresh vive en cookie `HttpOnly`. El acceso JWT de 15 minutos está en
  memoria del cliente.
- Las escrituras sin red se rechazan; no hay cola de POST.
- Las purgas las corre el servicio `worker` de Compose.
