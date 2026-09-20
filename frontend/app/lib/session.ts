'use client';

import { useEffect, useState } from 'react';

import type { User } from '../types/api';
import { api, getAccessToken, hasSession } from './api';

/**
 * Sesión de la usuaria, con sus permisos.
 *
 * La caché se indexa por el token de acceso vigente. El acceso vive en
 * memoria; un aviso en sessionStorage indica que hay cookie de refresh, para
 * que una recarga intente `/me` (y renueve) en vez de echar a la usuaria.
 *
 * `user` y `loading` se derivan durante el render; el efecto solo escribe
 * estado desde la respuesta asíncrona, nunca de forma síncrona.
 */
let cache: { token: string; user: User } | null = null;

type Resolved = { token: string | null; user: User | null };

export function useSession() {
  const token = getAccessToken();
  const pending = hasSession();
  const [resolved, setResolved] = useState<Resolved | null>(null);

  const fromCache = cache && cache.token === token ? cache.user : null;
  const fromFetch =
    resolved && resolved.token === token ? resolved.user : null;
  const user = fromCache ?? fromFetch;
  const settled =
    !pending || fromCache !== null || resolved !== null;

  useEffect(() => {
    if (!pending) return;
    if (token && cache && cache.token === token) return;
    let alive = true;
    // `/me` no usa `apiCached`: un permiso rancio abriría o cerraría pantallas.
    api<User>('/me')
      .then((value) => {
        const current = getAccessToken();
        if (current) cache = { token: current, user: value };
        if (alive) setResolved({ token: current, user: value });
      })
      .catch(() => {
        if (alive) setResolved({ token: getAccessToken(), user: null });
      });
    return () => {
      alive = false;
    };
  }, [token, pending]);

  return {
    user,
    loading: !settled,
    /** Usa los mismos códigos que verifica `assert_permission` en el backend. */
    has: (permission: string) =>
      Boolean(user?.permissions.includes(permission)),
  };
}
