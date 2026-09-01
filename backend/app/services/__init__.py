"""Casos de uso de la aplicación.

Los servicios reciben una `Session` de SQLAlchemy, coordinan reglas de dominio,
persistencia y auditoría, y son los dueños de la transacción: un `commit` por
caso de uso. No importan `fastapi`; señalan errores con `app.core.exceptions`.
"""
