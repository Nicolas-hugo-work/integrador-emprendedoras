'use client';

import { SubmitEvent, useCallback, useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue } from '../lib/form';
import { useSession } from '../lib/session';
import type { AuditEvent } from '../types/api';

const PAGE_SIZE = 25;

const RESULT_STYLE: Record<string, string> = {
  SUCCESS: 'bg-emerald-50 text-emerald-700',
  DENIED: 'bg-amber-50 text-amber-800',
  FAILED: 'bg-red-50 text-red-700',
};

type Filters = { action: string; object_type: string };

function describe(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : 'No se pudo cargar la traza.';
}

export default function AuditPage() {
  const { has, loading: loadingSession } = useSession();
  const canRead = has('audit.read');

  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filters, setFilters] = useState<Filters>({
    action: '',
    object_type: '',
  });
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (current: Filters, offsetPage: number) => {
    const query = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offsetPage * PAGE_SIZE),
    });
    if (current.action) query.set('action', current.action);
    if (current.object_type) query.set('object_type', current.object_type);
    return api<AuditEvent[]>(`/audit-events?${query.toString()}`);
  }, []);

  useEffect(() => {
    if (!canRead) return;
    let alive = true;
    void (async () => {
      try {
        const listed = await load(filters, page);
        if (alive) setEvents(listed);
      } catch (reason) {
        if (alive) setError(describe(reason));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [canRead, filters, page, load]);

  function applyFilters(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setPage(0);
    setFilters({
      action: fieldValue(data, 'action').trim(),
      object_type: fieldValue(data, 'object_type').trim(),
    });
  }

  if (loadingSession) {
    return (
      <AppShell eyebrow="Traza verificable" title="Auditoría">
        <div className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  if (!canRead) {
    return (
      <AppShell eyebrow="Traza verificable" title="Auditoría">
        <div className="mx-auto max-w-lg rounded-3xl border bg-card p-8 text-center">
          <ShieldAlert className="mx-auto size-10 text-amber-600" />
          <h2 className="mt-4 font-heading text-xl font-bold">
            No tienes acceso a la auditoría
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Esta sección requiere el permiso <code>audit.read</code>.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell eyebrow="Traza verificable" title="Auditoría">
      <div className="space-y-6">
        <div className="rounded-3xl border bg-card p-6">
          <div className="flex items-start gap-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/8 text-primary">
              <ScrollText className="size-5" />
            </span>
            <div>
              <h2 className="font-heading text-lg font-bold">
                Registro de eventos
              </h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                La tabla no admite modificaciones ni borrados: dos disparadores
                en la base lo impiden. Quien actuó aparece siempre
                seudonimizado.
              </p>
            </div>
          </div>

          <form
            onSubmit={applyFilters}
            className="mt-5 flex flex-wrap items-end gap-3"
          >
            <label className="text-sm font-semibold">
              Acción
              <input
                name="action"
                defaultValue={filters.action}
                placeholder="business.create"
                className="field"
              />
            </label>
            <label className="text-sm font-semibold">
              Tipo de objeto
              <input
                name="object_type"
                defaultValue={filters.object_type}
                placeholder="business"
                className="field"
              />
            </label>
            <button className="h-11 rounded-xl bg-primary px-5 text-sm font-bold text-white">
              Filtrar
            </button>
          </form>
        </div>

        {error && (
          <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {error}
          </p>
        )}

        <section className="rounded-3xl border bg-card p-6">
          {loading ? (
            <div className="grid min-h-40 place-items-center">
              <LoaderCircle className="animate-spin text-primary" />
            </div>
          ) : events.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="py-3 pr-4 font-bold">Fecha</th>
                    <th className="py-3 pr-4 font-bold">Acción</th>
                    <th className="py-3 pr-4 font-bold">Objeto</th>
                    <th className="py-3 pr-4 font-bold">Actora</th>
                    <th className="py-3 font-bold">Resultado</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {events.map((item) => (
                    <tr key={item.id}>
                      <td className="py-3 pr-4 whitespace-nowrap text-muted-foreground">
                        {new Date(item.occurred_at).toLocaleString('es-BO')}
                      </td>
                      <td className="py-3 pr-4 font-semibold">{item.action}</td>
                      <td className="py-3 pr-4 text-muted-foreground">
                        {item.object_type}
                      </td>
                      <td
                        className="py-3 pr-4 font-mono text-xs text-muted-foreground"
                        title={`Huella de integridad: ${item.integrity_hash}`}
                      >
                        {item.actor_pseudonym.slice(0, 12)}…
                      </td>
                      <td className="py-3">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-bold ${RESULT_STYLE[item.result] ?? 'bg-muted'}`}
                        >
                          {item.result}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No hay eventos que coincidan con el filtro.
            </p>
          )}

          <div className="mt-5 flex items-center justify-between border-t pt-4">
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4 text-emerald-600" />
              Cada evento lleva su huella de integridad.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                aria-label="Página anterior"
                className="grid size-9 place-items-center rounded-lg border disabled:opacity-40"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="text-sm font-semibold">{page + 1}</span>
              <button
                type="button"
                disabled={events.length < PAGE_SIZE}
                onClick={() => setPage((current) => current + 1)}
                aria-label="Página siguiente"
                className="grid size-9 place-items-center rounded-lg border disabled:opacity-40"
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
