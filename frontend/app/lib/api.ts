import type { TokenPair } from '../types/api';
import {
  clearOfflineCache,
  readCached,
  shouldReuseOnFailure,
  shouldStore,
  writeCached,
} from './offline-cache';

export type { TokenPair };

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const ACCESS_KEY = 'kawsay_access';
const REFRESH_KEY = 'kawsay_refresh';

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

function readToken(key: string): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(key);
}

export function saveTokens(tokens: TokenPair) {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  void clearOfflineCache();
}

export function hasSession() {
  return Boolean(readToken(ACCESS_KEY));
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
 * El token de acceso dura 15 minutos. Hasta v0.1.0 el `refresh_token` se
 * guardaba pero no se usaba nunca, así que al vencer el acceso la usuaria
 * quedaba fuera sin aviso y sin forma de recuperarse. Varias peticiones que
 * fallan a la vez comparten un único intento de renovación.
 */
let refreshInFlight: Promise<boolean> | null = null;

async function performRefresh(): Promise<boolean> {
  const refreshToken = readToken(REFRESH_KEY);
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
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
  clearTokens();
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

function send(path: string, init: RequestInit, authenticated: boolean) {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (authenticated) {
    const token = readToken(ACCESS_KEY);
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(`${API_URL}${path}`, { ...init, headers });
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
    throw reason instanceof Error
      ? reason
      : new NetworkError(false);
  }
}

/** Solo para pruebas: olvida la renovación en curso entre casos. */
export function __resetRefreshState() {
  refreshInFlight = null;
}
