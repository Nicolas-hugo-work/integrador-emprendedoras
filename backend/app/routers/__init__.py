"""Routers HTTP.

Los routers solo traducen protocolo: schemas de entrada, dependencias, códigos
de estado y forma de la respuesta. No importan `sqlalchemy` ni `app.models`, y
no ejecutan `commit`, `flush` ni `refresh`: la transacción pertenece al
servicio. `tests/test_architecture.py` verifica ambas reglas.
"""
