export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export function saveTokens(tokens: TokenPair) {
  sessionStorage.setItem('kawsay_access', tokens.access_token);
  sessionStorage.setItem('kawsay_refresh', tokens.refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem('kawsay_access');
  sessionStorage.removeItem('kawsay_refresh');
}

export function hasSession() {
  return typeof window !== 'undefined' && Boolean(sessionStorage.getItem('kawsay_access'));
}

export async function api<T>(path: string, init: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (authenticated && typeof window !== 'undefined') {
    const token = sessionStorage.getItem('kawsay_access');
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = 'No se pudo completar la solicitud.';
    try {
      const error = await response.json();
      message = typeof error.detail === 'string' ? error.detail : message;
    } catch { /* respuesta sin JSON */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
