import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  __resetRefreshState,
  api,
  clearTokens,
  hasSession,
  saveTokens,
} from '../app/lib/api';

/** `sessionStorage` mínimo en memoria, suficiente para el cliente HTTP. */
function createStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => void values.set(key, value),
    removeItem: (key: string) => void values.delete(key),
  };
}

let location: { pathname: string; href: string };

beforeEach(() => {
  location = { pathname: '/finanzas', href: '/finanzas' };
  vi.stubGlobal('sessionStorage', createStorage());
  vi.stubGlobal('window', { location });
  __resetRefreshState();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const TOKENS = {
  access_token: 'acceso-1',
  refresh_token: 'refresco-1',
  token_type: 'bearer',
  expires_in: 900,
};

describe('almacenamiento de sesión', () => {
  it('guarda, detecta y limpia la sesión', () => {
    expect(hasSession()).toBe(false);
    saveTokens(TOKENS);
    expect(hasSession()).toBe(true);
    clearTokens();
    expect(hasSession()).toBe(false);
  });
});

describe('cliente HTTP', () => {
  it('adjunta el token de acceso en las peticiones autenticadas', async () => {
    saveTokens(TOKENS);
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse([{ id: 'negocio-1' }]));
    vi.stubGlobal('fetch', fetchMock);

    await api('/businesses');

    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init.headers).get('Authorization')).toBe(
      'Bearer acceso-1',
    );
  });

  it('no adjunta el token cuando la petición es pública', async () => {
    saveTokens(TOKENS);
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(TOKENS));
    vi.stubGlobal('fetch', fetchMock);

    await api('/auth/login', { method: 'POST' }, false);

    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init.headers).get('Authorization')).toBeNull();
  });

  it('propaga el detail del backend como mensaje de error', async () => {
    saveTokens(TOKENS);
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ detail: 'Emprendimiento no encontrado' }, 404),
        ),
    );

    await expect(api('/finance/summary')).rejects.toThrow(
      'Emprendimiento no encontrado',
    );
  });

  it('usa un mensaje genérico si la respuesta no trae JSON', async () => {
    saveTokens(TOKENS);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('vaya', { status: 500 })),
    );

    await expect(api('/finance/summary')).rejects.toThrow(
      'No se pudo completar la solicitud.',
    );
  });
});

describe('renovación de sesión ante un 401', () => {
  it('renueva el acceso y reintenta la petición original', async () => {
    saveTokens(TOKENS);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'Token vencido' }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ ...TOKENS, access_token: 'acceso-2' }),
      )
      .mockResolvedValueOnce(jsonResponse({ balance: '10.00' }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await api<{ balance: string }>('/finance/summary');

    expect(result).toEqual({ balance: '10.00' });
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh');
    const [, retryInit] = fetchMock.mock.calls[2];
    expect(new Headers(retryInit.headers).get('Authorization')).toBe(
      'Bearer acceso-2',
    );
    expect(sessionStorage.getItem('kawsay_access')).toBe('acceso-2');
  });

  it('cierra la sesión y redirige cuando la renovación falla', async () => {
    saveTokens(TOKENS);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'Token vencido' }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'Sesión inválida o vencida' }, 401),
      );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api('/finance/summary')).rejects.toThrow(
      'Tu sesión expiró. Vuelve a ingresar.',
    );
    expect(hasSession()).toBe(false);
    expect(location.href).toBe('/login');
  });

  it('no intenta renovar si no hay token de refresco', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({ detail: 'Autenticación requerida' }, 401),
      );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api('/me')).rejects.toThrow('Tu sesión expiró.');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('comparte una sola renovación entre peticiones simultáneas', async () => {
    saveTokens(TOKENS);
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/refresh')) {
        return Promise.resolve(
          jsonResponse({ ...TOKENS, access_token: 'acceso-2' }),
        );
      }
      const token = sessionStorage.getItem('kawsay_access');
      return Promise.resolve(
        token === 'acceso-2'
          ? jsonResponse({ ok: true })
          : jsonResponse({ detail: 'Token vencido' }, 401),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await Promise.all([api('/businesses'), api('/conversations')]);

    const refreshCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes('/auth/refresh'),
    );
    expect(refreshCalls).toHaveLength(1);
  });

  it('no renueva ante un 401 de una petición pública', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({ detail: 'Credenciales inválidas' }, 401),
      );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api('/auth/login', { method: 'POST' }, false)).rejects.toThrow(
      'Credenciales inválidas',
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
