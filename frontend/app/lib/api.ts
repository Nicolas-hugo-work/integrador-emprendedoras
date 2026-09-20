import type { TokenPair } from '../types/api';
import {
  clearOfflineCache,
  readCached,
  shouldReuseOnFailure,
  shouldStore,
  writeCached,
} from './offline-cache';

export type { TokenPair };

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '/api';

const SESSION_HINT = 'kawsay_session';

const GENERIC_ERROR = 'No se pudo completar la solicitud.';
const EXPIRED_ERROR = 'Tu sesión expiró. Vuelve a ingresar.';
export const NETWORK_ERROR =
  'No hay conexión. Inténtalo de nuevo cuando vuelva.';
export const OFFLINE_WRITE_ERROR =
  'No se guardó porque no hay conexión; vuelve a intentarlo cuando vuelva.';

export class NetworkError extends Error {
  readonly write: boolean;

  constructor(write = false) {
    super(write ? OFFLINE_WRITE_ERROR : NETWORK_ERROR);
    this.name = 'NetworkError';
    this.write = write;
  }
}

export type CachedResult<T> = {
  data: T;
  fetchedAt: Date | null;
  stale: boolean;
};

let accessToken: string | null = null;

function hintOn(): boolean {
  if (typeof window === 'undefined') return false;
  return sessionStorage.getItem(SESSION_HINT) === '1';
}

function setHint(on: boolean) {
  if (typeof window === 'undefined') return;
  if (on) sessionStorage.setItem(SESSION_HINT, '1');
  else sessionStorage.removeItem(SESSION_HINT);
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function saveTokens(tokens: TokenPair) {
  accessToken = tokens.access_token;
  setHint(true);
}

export function clearTokens() {
  const previous = accessToken;
  accessToken = null;
  setHint(false);
  if (typeof window === 'undefined') return;
  void clearOfflineCache();
  if (previous && typeof window !== 'undefined') {
    const origin = window.location.origin || 'http://localhost';
    const url = API_URL.startsWith('http')
      ? `${API_URL}/auth/logout`
      : `${origin}${API_URL}/auth/logout`;
    void fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${previous}`,
      },
    }).catch(() => {
      /* el aviso de sesión ya se borró */
    });
  }
}

export function hasSession() {
  return Boolean(accessToken || hintOn());
}

/**
 * Un `fetch` que no llega al servidor rechaza. Una respuesta HTTP, aunque sea
 * 500, resuelve. Distinguir los dos es lo que evita servir un saldo viejo
 * cuando el backend sí contestó «no».
 */
export function isFetchFailure(reason: unknown): boolean {
  if (reason instanceof TypeError) return true;
  if (!(reason instanceof Error)) return false;
  const message = reason.message.toLowerCase();
  return (
    message.includes('failed to fetch') ||
    message.includes('networkerror') ||
    message.includes('load failed') ||
    message.includes('network request failed')
  );
}

export function isNetworkError(reason: unknown): boolean {
  return reason instanceof NetworkError || isFetchFailure(reason);
}

function isWriteMethod(method: string | undefined): boolean {
  const verb = (method ?? 'GET').toUpperCase();
  return verb !== 'GET' && verb !== 'HEAD';
}

function asNetworkError(
  reason: unknown,
  method: string | undefined,
): NetworkError {
  if (reason instanceof NetworkError) return reason;
  return new NetworkError(isWriteMethod(method));
}

/**
 * Renovación de sesión compartida.
 *
 * El refresh vive en cookie HttpOnly. El acceso de 15 minutos está en memoria:
 * al recargar, este POST lo renueva. Varias peticiones que fallan a la vez
 * comparten un único intento.
 */
let refreshInFlight: Promise<boolean> | null = null;

async function performRefresh(): Promise<boolean> {
  if (!hintOn() && !accessToken) return false;
  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) return false;
    saveTokens((await response.json()) as TokenPair);
    return true;
  } catch (reason) {
    if (isFetchFailure(reason)) throw new NetworkError(false);
    return false;
  }
}

function refreshSession(): Promise<boolean> {
  refreshInFlight ??= performRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

function endSession() {
  accessToken = null;
  setHint(false);
  if (typeof window !== 'undefined') {
    void clearOfflineCache();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
}

function send(path: string, init: RequestInit, authenticated: boolean) {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (authenticated && accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
}

async function toError(response: Response): Promise<Error> {
  let message = GENERIC_ERROR;
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') message = body.detail;
  } catch {
    /* respuesta sin JSON */
  }
  return new Error(message);
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const method = init.method ?? 'GET';
  try {
    let response: Response;
    try {
      response = await send(path, init, authenticated);
    } catch (reason) {
      throw asNetworkError(reason, method);
    }

    if (response.status === 401 && authenticated) {
      try {
        if (await refreshSession()) {
          try {
            response = await send(path, init, authenticated);
          } catch (reason) {
            throw asNetworkError(reason, method);
          }
        } else {
          endSession();
          throw new Error(EXPIRED_ERROR);
        }
      } catch (reason) {
        if (reason instanceof NetworkError) throw reason;
        if (isFetchFailure(reason)) throw asNetworkError(reason, method);
        throw reason;
      }
    }

    if (!response.ok) throw await toError(response);
    return response.json() as Promise<T>;
  } catch (reason) {
    if (reason instanceof NetworkError) throw reason;
    if (isFetchFailure(reason)) throw asNetworkError(reason, method);
    throw reason;
  }
}

/**
 * GET que recuerda la última respuesta buena. Ante un fallo de red —no HTTP—
 * devuelve esa copia con `stale: true`. `api()` conserva su firma y sigue
 * lanzando: la llaman más de cuarenta sitios.
 */
export async function apiCached<T>(path: string): Promise<CachedResult<T>> {
  try {
    const data = await api<T>(path);
    const fetchedAt = new Date();
    if (shouldStore('GET', true)) {
      await writeCached(path, data, fetchedAt);
    }
    return { data, fetchedAt, stale: false };
  } catch (reason) {
    if (shouldReuseOnFailure('GET', isNetworkError(reason))) {
      const cached = await readCached<T>(path);
      if (cached) {
        return { data: cached.data, fetchedAt: cached.fetchedAt, stale: true };
      }
    }
    throw reason instanceof Error ? reason : new NetworkError(false);
  }
}

/** Solo para pruebas: olvida la renovación en curso entre casos. */
export function __resetRefreshState() {
  refreshInFlight = null;
  accessToken = null;
}
