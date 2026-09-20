'use client';

import { useEffect, useState } from 'react';

export function PwaRegister() {
  const [updateReady, setUpdateReady] = useState(false);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    let cancelled = false;
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        registration.addEventListener('updatefound', () => {
          const worker = registration.installing;
          if (!worker) return;
          worker.addEventListener('statechange', () => {
            if (
              worker.state === 'installed' &&
              navigator.serviceWorker.controller &&
              !cancelled
            ) {
              setUpdateReady(true);
            }
          });
        });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (!updateReady) return null;
  return (
    <output className="block w-full bg-primary px-4 py-2.5 text-center text-sm font-semibold text-primary-foreground">
      Hay una versión nueva de Kawsay.
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="rounded-lg bg-white px-3 py-1 text-xs font-bold text-primary"
      >
        Actualizar
      </button>
    </output>
  );
}
