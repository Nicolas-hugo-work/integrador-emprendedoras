import Link from 'next/link';
import { WifiOff } from 'lucide-react';

export const metadata = {
  title: 'Sin conexión',
};

export default function OfflinePage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-5 text-foreground">
      <div className="w-full max-w-md rounded-3xl border bg-card p-8 text-center shadow-sm">
        <span className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-primary/8 text-primary">
          <WifiOff className="size-7" />
        </span>
        <h1 className="font-heading text-2xl font-bold">No hay conexión</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Puedes seguir viendo las pantallas que ya abriste. Los números que
          aparezcan serán los últimos que se pudieron cargar, con su fecha. No
          se puede guardar nada nuevo hasta que vuelva la red.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex h-11 items-center justify-center rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground"
        >
          Ir al inicio
        </Link>
      </div>
    </main>
  );
}
