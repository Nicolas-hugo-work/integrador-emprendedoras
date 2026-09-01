"""Excepciones de aplicación independientes de FastAPI.

Los servicios señalan errores con estas clases; `main.py` las traduce a
respuestas HTTP mediante un único manejador. De esta forma la capa de casos de
uso no importa `fastapi` y puede probarse sin cliente HTTP.

El atributo `status` conserva exactamente el código que devolvía `v0.1.0`.
"""


class AppError(Exception):
    """Error de aplicación con un código HTTP asociado."""

    status: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class Invalid(AppError):
    """La solicitud es sintácticamente válida pero incumple una regla."""

    status = 422


class Unauthorized(AppError):
    """Falta autenticación o las credenciales no son válidas."""

    status = 401


class Forbidden(AppError):
    """La usuaria está autenticada pero carece del permiso requerido."""

    status = 403


class NotFound(AppError):
    """El recurso no existe o no pertenece a la usuaria.

    Se usa también para accesos horizontales: nunca se distingue entre
    "no existe" y "existe pero es de otra persona".
    """

    status = 404


class Conflict(AppError):
    """El estado actual del recurso impide la operación."""

    status = 409


class BadRequest(AppError):
    """La solicitud no puede procesarse tal como viene."""

    status = 400


class TooManyRequests(AppError):
    """Se superó el límite de intentos permitido."""

    status = 429


class Unavailable(AppError):
    """Falta una precondición del sistema, no de la solicitud."""

    status = 500
