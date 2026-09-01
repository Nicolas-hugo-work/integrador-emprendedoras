'use client';

import { useEffect, useState } from 'react';

import type { User } from '../types/api';
import { api } from './api';

/**
 * Sesión de la usuaria, con sus permisos.
 *
 * La caché se indexa por el token de acceso vigente, de modo que cerrar sesión
 * e ingresar con otra cuenta invalida el perfil anterior sin que nadie tenga
 * que limpiarlo a mano.
 *
 * `user` y `loading` se derivan durante el render; el efecto solo escribe
 * estado desde la respuesta asíncrona, nunca de forma síncrona.
 */
let cache: { token: string; user: User } | null = null;

function currentToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return sessionStorage.getItem('kawsay_access');
  } catch {
    return null;
  }
}

type Resolved = { token: string; user: User | null };

export function useSession() {
  const token = currentToken();
  const [resolved, setResolved] = useState<Resolved | null>(null);

  const fromCache = cache && cache.token === token ? cache.user : null;
  const fromFetch = resolved && resolved.token === token ? resolved.user : null;
  const user = fromCache ?? fromFetch;
  const settled = !token || fromCache !== null || resolved?.token === token;

  useEffect(() => {
    if (!token || (cache && cache.token === token)) return;
    let alive = true;
    api<User>('/me')
      .then((value) => {
        cache = { token, user: value };
        if (alive) setResolved({ token, user: value });
      })
      .catch(() => {
        if (alive) setResolved({ token, user: null });
      });
    return () => {
      alive = false;
    };
  }, [token]);

  return {
    user,
    loading: !settled,
    /** Usa los mismos códigos que verifica `assert_permission` en el backend. */
    has: (permission: string) =>
      Boolean(user?.permissions.includes(permission)),
  };
}
