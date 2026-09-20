/**
 * Última respuesta buena de cada GET, con su marca de tiempo.
 *
 * IndexedDB y no `localStorage`: son JSON completos, y hoy el proyecto no usa
 * ninguna de las dos (solo `sessionStorage` para los tokens).
 */

const DB_NAME = 'kawsay-offline';
const STORE = 'responses';
const DB_VERSION = 1;

type Entry = {
  path: string;
  data: unknown;
  fetchedAt: string;
};

export type CachedEntry<T> = {
  data: T;
  fetchedAt: Date;
};

/** Solo un GET exitoso se guarda. Un POST no, ni un 404. */
export function shouldStore(
  method: string | undefined,
  ok: boolean,
): boolean {
  return (method ?? 'GET').toUpperCase() === 'GET' && ok;
}

/** La copia vieja solo se sirve ante un fallo de red, nunca ante un HTTP. */
export function shouldReuseOnFailure(
  method: string | undefined,
  networkFailure: boolean,
): boolean {
  return (method ?? 'GET').toUpperCase() === 'GET' && networkFailure;
}

function available(): boolean {
  return typeof indexedDB !== 'undefined';
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'path' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function readCached<T>(
  path: string,
): Promise<CachedEntry<T> | null> {
  if (!available()) return null;
  try {
    const db = await openDb();
    const entry = await new Promise<Entry | undefined>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const request = tx.objectStore(STORE).get(path);
      request.onsuccess = () => resolve(request.result as Entry | undefined);
      request.onerror = () => reject(request.error);
    });
    db.close();
    if (!entry) return null;
    return { data: entry.data as T, fetchedAt: new Date(entry.fetchedAt) };
  } catch {
    return null;
  }
}

export async function writeCached(
  path: string,
  data: unknown,
  fetchedAt: Date = new Date(),
): Promise<void> {
  if (!available()) return;
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put({
        path,
        data,
        fetchedAt: fetchedAt.toISOString(),
      } satisfies Entry);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* el caché es una mejora, no una dependencia */
  }
}

export async function clearOfflineCache(): Promise<void> {
  if (!available()) return;
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* igual que write: no bloquear el cierre de sesión */
  }
}
