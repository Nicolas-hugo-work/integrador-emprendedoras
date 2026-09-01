import type { TokenPair } from '../types/api';

export type { TokenPair };

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const ACCESS_KEY = 'kawsay_access';
const REFRESH_KEY = 'kawsay_refresh';

const GENERIC_ERROR = 'No se pudo completar la solicitud.';
const EXPIRED_ERROR = 'Tu sesión expiró. Vuelve a ingresar.';

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
}

export function hasSession() {
  return Boolean(readToken(ACCESS_KEY));
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
  } catch {
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
  let response = await send(path, init, authenticated);

  if (response.status === 401 && authenticated) {
    if (await refreshSession()) {
      response = await send(path, init, authenticated);
    } else {
      endSession();
      throw new Error(EXPIRED_ERROR);
    }
  }

  if (!response.ok) throw await toError(response);
  return response.json() as Promise<T>;
}

/** Solo para pruebas: olvida la renovación en curso entre casos. */
export function __resetRefreshState() {
  refreshInFlight = null;
}
