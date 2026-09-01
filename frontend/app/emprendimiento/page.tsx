'use client';

import { SubmitEvent, useEffect, useState } from 'react';
import {
  Building2,
  CheckCircle2,
  LoaderCircle,
  MapPin,
  Sparkles,
} from 'lucide-react';
import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue, optionalFieldValue } from '../lib/form';

import type { Business } from '../types/api';

export default function BusinessPage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    api<Business[]>('/businesses')
      .then(setBusinesses)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setError('');
    try {
      const created = await api<Business>('/businesses', {
        method: 'POST',
        body: JSON.stringify({
          name: fieldValue(data, 'name'),
          stage: fieldValue(data, 'stage'),
          activity: fieldValue(data, 'activity'),
          department_code: optionalFieldValue(data, 'department_code'),
          municipality: optionalFieldValue(data, 'municipality'),
        }),
      });
      setBusinesses([created, ...businesses]);
      form.reset();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo guardar.',
      );
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
                Datos del negocio
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Guardamos únicamente ubicación general, nunca tu domicilio
                exacto.
              </p>
            </div>
          </div>
          <form onSubmit={submit} className="grid gap-5 sm:grid-cols-2">
            <label className="text-sm font-semibold sm:col-span-2">
              Nombre del emprendimiento
              <input
                name="name"
                required
                className="field"
                placeholder="Ej. Tejidos Esperanza"
              />
            </label>
            <label className="text-sm font-semibold">
              Etapa
              <select name="stage" className="field">
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
                className="field"
                placeholder="Artesanía, alimentos…"
              />
            </label>
            <label className="text-sm font-semibold">
              Departamento
              <input
                name="department_code"
                className="field"
                placeholder="LP, CB, SC…"
              />
            </label>
            <label className="text-sm font-semibold">
              Municipio
              <input name="municipality" className="field" />
            </label>
            {error && (
              <p className="sm:col-span-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                {error}
              </p>
            )}
            <button className="h-12 rounded-xl bg-primary px-6 font-bold text-white sm:col-span-2">
              Guardar emprendimiento
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
                    <div className="flex items-center justify-between">
                      <strong>{item.name}</strong>
                      <CheckCircle2 className="size-4 text-emerald-600" />
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
