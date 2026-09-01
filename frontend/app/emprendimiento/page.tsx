'use client';

import { SubmitEvent, useEffect, useState } from 'react';
import {
  Building2,
  CheckCircle2,
  LoaderCircle,
  MapPin,
  Pencil,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue, optionalFieldValue } from '../lib/form';
import type { Business } from '../types/api';

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function BusinessPage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [editing, setEditing] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const listed = await api<Business[]>('/businesses');
        if (alive) setBusinesses(listed);
      } catch (reason) {
        if (alive) setError(describe(reason, 'No se pudo cargar.'));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setError('');
    const body = {
      name: fieldValue(data, 'name'),
      stage: fieldValue(data, 'stage'),
      activity: fieldValue(data, 'activity'),
      department_code: optionalFieldValue(data, 'department_code'),
      municipality: optionalFieldValue(data, 'municipality'),
    };
    try {
      if (editing) {
        const updated = await api<Business>(`/businesses/${editing.id}`, {
          method: 'PATCH',
          body: JSON.stringify(body),
        });
        setBusinesses((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
        setEditing(null);
      } else {
        const created = await api<Business>('/businesses', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        setBusinesses((current) => [created, ...current]);
      }
      form.reset();
    } catch (reason) {
      setError(describe(reason, 'No se pudo guardar.'));
    }
  }

  async function remove(business: Business) {
    const confirmed = confirm(
      `Se archivará ${business.name}. Tu historial financiero se conserva. ¿Continuar?`,
    );
    if (!confirmed) return;
    setError('');
    try {
      await api(`/businesses/${business.id}`, { method: 'DELETE' });
      setBusinesses((current) =>
        current.filter((item) => item.id !== business.id),
      );
      if (editing?.id === business.id) setEditing(null);
    } catch (reason) {
      setError(describe(reason, 'No se pudo eliminar.'));
    }
  }

  return (
    <AppShell eyebrow="Perfil productivo" title="Mi emprendimiento">
      <div className="grid gap-6 xl:grid-cols-[1fr_0.85fr]">
        <section className="rounded-3xl border bg-card p-6 shadow-sm">
          <div className="mb-7 flex items-start gap-4">
            <span className="grid size-12 place-items-center rounded-2xl bg-primary/8 text-primary">
              <Building2 />
            </span>
            <div>
              <h2 className="font-heading text-xl font-bold">
                {editing ? 'Corregir emprendimiento' : 'Datos del negocio'}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Guardamos únicamente ubicación general, nunca tu domicilio
                exacto.
              </p>
            </div>
          </div>
          {editing && (
            <button
              type="button"
              onClick={() => setEditing(null)}
              className="mb-4 flex items-center gap-1 text-sm font-semibold text-muted-foreground"
            >
              <X className="size-4" /> Cancelar corrección
            </button>
          )}
          <form
            key={editing?.id ?? 'nuevo'}
            onSubmit={submit}
            className="grid gap-5 sm:grid-cols-2"
          >
            <label className="text-sm font-semibold sm:col-span-2">
              Nombre del emprendimiento
              <input
                name="name"
                required
                defaultValue={editing?.name ?? ''}
                className="field"
                placeholder="Ej. Tejidos Esperanza"
              />
            </label>
            <label className="text-sm font-semibold">
              Etapa
              <select
                name="stage"
                defaultValue={editing?.stage ?? 'IDEA'}
                className="field"
              >
                <option value="IDEA">Tengo una idea</option>
                <option value="STARTUP">Estoy comenzando</option>
                <option value="OPERATING">Ya está funcionando</option>
                <option value="GROWING">Está creciendo</option>
                <option value="PAUSED">Está en pausa</option>
              </select>
            </label>
            <label className="text-sm font-semibold">
              Actividad
              <input
                name="activity"
                required
                defaultValue={editing?.activity ?? ''}
                className="field"
                placeholder="Artesanía, alimentos…"
              />
            </label>
            <label className="text-sm font-semibold">
              Departamento
              <input
                name="department_code"
                defaultValue={editing?.department_code ?? ''}
                className="field"
                placeholder="LP, CB, SC…"
              />
            </label>
            <label className="text-sm font-semibold">
              Municipio
              <input
                name="municipality"
                defaultValue={editing?.municipality ?? ''}
                className="field"
              />
            </label>
            {error && (
              <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 sm:col-span-2">
                {error}
              </p>
            )}
            <button className="h-12 rounded-xl bg-primary px-6 font-bold text-white sm:col-span-2">
              {editing ? 'Guardar corrección' : 'Guardar emprendimiento'}
            </button>
          </form>
        </section>
        <section className="space-y-4">
          <div className="rounded-3xl bg-[#123d38] p-6 text-white">
            <Sparkles className="mb-5 size-7 text-[#efc98d]" />
            <h2 className="font-heading text-xl font-bold">
              Tu información mejora las orientaciones
            </h2>
            <p className="mt-2 text-sm leading-6 text-white/70">
              La etapa y actividad permiten adaptar los ejemplos de costos,
              precios y formalización.
            </p>
          </div>
          <div className="rounded-3xl border bg-card p-6">
            <h2 className="font-heading text-lg font-bold">
              Emprendimientos registrados
            </h2>
            {loading ? (
              <LoaderCircle className="mt-6 animate-spin text-primary" />
            ) : businesses.length ? (
              <div className="mt-4 space-y-3">
                {businesses.map((item) => (
                  <article key={item.id} className="rounded-2xl border p-4">
                    <div className="flex items-center justify-between gap-2">
                      <strong className="min-w-0 truncate">{item.name}</strong>
                      <div className="flex shrink-0 items-center gap-1">
                        <CheckCircle2 className="size-4 text-emerald-600" />
                        <button
                          type="button"
                          onClick={() => setEditing(item)}
                          aria-label={`Corregir ${item.name}`}
                          className="grid size-8 place-items-center rounded-lg border text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="size-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(item)}
                          aria-label={`Eliminar ${item.name}`}
                          className="grid size-8 place-items-center rounded-lg border border-red-200 text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {item.activity}
                    </p>
                    {item.municipality && (
                      <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        <MapPin className="size-3" /> {item.municipality}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">
                Aún no registraste un emprendimiento.
              </p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
