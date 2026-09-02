"""Límite de intentos con retroceso progresivo.

Argon2id encarece cada verificación de contraseña, pero no impide intentos
ilimitados: `v0.1.0` no tenía ningún límite en `/auth/login` ni en
`/auth/verify-contact`.

El contador vive en memoria del proceso a propósito. La alternativa —una tabla
nueva— cambiaría el esquema, y un criterio de aceptación del plan es que la
huella de `information_schema` quede idéntica. Con un solo contenedor de
backend (el de `docker-compose.yml`) el límite es efectivo. Migrar a Redis o a
una tabla dedicada queda anotado para v0.3.0.
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Attempts:
    failures: list[float] = field(default_factory=list)
    blocked_until: float = 0.0


class AttemptLimiter:
    """Ventana deslizante de fallos con bloqueo que se duplica en cada exceso.

    Tras `max_attempts` fallos dentro de `window_seconds`, la clave queda
    bloqueada `block_seconds`; cada fallo adicional duplica la espera hasta
    `max_block_seconds`.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 5,
        window_seconds: float = 900.0,
        block_seconds: float = 60.0,
        max_block_seconds: float = 3600.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        self.max_block_seconds = max_block_seconds
        self._entries: dict[str, _Attempts] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def retry_after(self, key: str) -> int:
        """Segundos que faltan para poder reintentar; 0 si no está bloqueada."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 0
            remaining = entry.blocked_until - self._now()
            return max(0, int(remaining) + 1) if remaining > 0 else 0

    def record_failure(self, key: str) -> bool:
        """Anota un intento fallido y actualiza el bloqueo si corresponde.

        Devuelve `True` solo cuando **este** intento provoca el bloqueo, no
        cuando la clave ya estaba bloqueada. Mientras lo está, `_guard` responde
        429 antes de llegar aquí, así que la transición ocurre como mucho una
        vez por ventana: quien consuma el valor puede levantar una alerta sin
        que se multipliquen solas.
        """
        now = self._now()
        with self._lock:
            entry = self._entries.setdefault(key, _Attempts())
            estaba_bloqueada = entry.blocked_until > now
            entry.failures = [t for t in entry.failures if now - t < self.window_seconds]
            entry.failures.append(now)
            excess = len(entry.failures) - self.max_attempts
            if excess < 0:
                return False
            penalty = min(self.block_seconds * (2**excess), self.max_block_seconds)
            entry.blocked_until = now + penalty
            return not estaba_bloqueada

    def reset(self, key: str) -> None:
        """Olvida los intentos de una clave tras un acceso correcto."""
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        """Vacía el limitador por completo (usado por las pruebas)."""
        with self._lock:
            self._entries.clear()


#: Intentos contra una misma cuenta, indexados por contacto normalizado.
login_limiter = AttemptLimiter(max_attempts=5, window_seconds=900, block_seconds=60)

#: Intentos desde una misma dirección. El umbral es más alto porque varias
#: usuarias legítimas pueden compartir salida NAT; su función es frenar el
#: rociado de contraseñas contra muchas cuentas distintas.
login_ip_limiter = AttemptLimiter(max_attempts=20, window_seconds=900, block_seconds=60)

#: Canje de códigos de verificación, indexados por dirección.
verification_limiter = AttemptLimiter(max_attempts=10, window_seconds=900, block_seconds=60)


def reset_all() -> None:
    """Vacía todos los limitadores (usado entre pruebas)."""
    for limiter in (login_limiter, login_ip_limiter, verification_limiter):
        limiter.clear()
