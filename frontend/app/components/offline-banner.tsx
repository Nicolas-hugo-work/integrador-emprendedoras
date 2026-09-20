'use client';

import { WifiOff } from 'lucide-react';
import { useOffline } from 'next/offline';

export function OfflineBanner() {
  const offline = useOffline();
  if (!offline) return null;
  return (
    <output className="block w-full bg-[#123d38] px-4 py-2.5 text-center text-sm font-semibold text-white">
      <WifiOff className="size-4 shrink-0" />
      Sin conexión. Se muestran los últimos datos que se pudieron cargar.
    </output>
  );
}
