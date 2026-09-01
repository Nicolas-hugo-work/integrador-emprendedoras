'use client';

import { SubmitEvent, useCallback, useEffect, useState } from 'react';
import {
  BookOpenCheck,
  CircleSlash,
  FileText,
  LoaderCircle,
  Plus,
  ShieldAlert,
  Upload,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue, optionalFieldValue } from '../lib/form';
import { useSession } from '../lib/session';
import type {
  Publisher,
  Source,
  SourceChunk,
  SourceVersion,
} from '../types/api';

const STATUS_STYLE: Record<string, string> = {
  DRAFT: 'bg-muted text-muted-foreground',
  IN_REVIEW: 'bg-amber-50 text-amber-800',
  REVIEW: 'bg-amber-50 text-amber-800',
  PUBLISHED: 'bg-emerald-50 text-emerald-700',
  RETIRED: 'bg-red-50 text-red-700',
};

function Badge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_STYLE[status] ?? 'bg-muted'}`}
    >
      {status}
    </span>
  );
}

/** Huella SHA-256 del documento, para `content_hash`. */
async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(text),
  );
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function describe(reason: unknown): string {
  return reason instanceof Error ? reason.message : 'No se pudo completar.';
}

function countWords(text: string): number {
  return Math.max(1, text.trim().split(/\s+/u).length);
}

export default function CurationPage() {
  const { has, loading: loadingSession } = useSession();
  const canReview = has('source.review');
  const canPublish = has('source.publish');

  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [selected, setSelected] = useState<Source | null>(null);
  const [versions, setVersions] = useState<SourceVersion[]>([]);
  const [chunks, setChunks] = useState<Record<string, SourceChunk[]>>({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const refreshSources = useCallback(async () => {
    setSources(await api<Source[]>('/sources'));
  }, []);

  const refreshVersions = useCallback(async (sourceId: string) => {
    setVersions(await api<SourceVersion[]>(`/sources/${sourceId}/versions`));
  }, []);

  useEffect(() => {
    if (!canReview) return;
    let alive = true;
    void (async () => {
      try {
        const [institutions, listed] = await Promise.all([
          api<Publisher[]>('/source-publishers'),
          api<Source[]>('/sources'),
        ]);
        if (!alive) return;
        setPublishers(institutions);
        setSources(listed);
      } catch (reason) {
        if (alive) setError(describe(reason));
      }
    })();
    return () => {
      alive = false;
    };
  }, [canReview]);

  // El guardia `alive` evita que la respuesta de una fuente ya deseleccionada
  // pise las versiones de la que la usuaria acaba de elegir.
  useEffect(() => {
    if (!selected) return;
    let alive = true;
    void (async () => {
      try {
        const listed = await api<SourceVersion[]>(
          `/sources/${selected.id}/versions`,
        );
        if (alive) setVersions(listed);
      } catch (reason) {
        if (alive) setError(describe(reason));
      }
    })();
    return () => {
      alive = false;
    };
  }, [selected]);

  async function run(action: () => Promise<void>, message: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(message);
    } catch (reason) {
      setError(describe(reason));
    } finally {
      setBusy(false);
    }
  }

  async function createSource(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await run(async () => {
      await api<{ id: string }>('/sources', {
        method: 'POST',
        body: JSON.stringify({
          publisher_id: fieldValue(data, 'publisher_id'),
          title: fieldValue(data, 'title'),
          canonical_url: fieldValue(data, 'canonical_url'),
          topic: fieldValue(data, 'topic'),
          license_name: optionalFieldValue(data, 'license_name'),
        }),
      });
      await refreshSources();
      form.reset();
    }, 'Fuente creada en borrador.');
  }

  async function createVersion(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const document = fieldValue(data, 'document');
    const label = fieldValue(data, 'version_label');
    await run(async () => {
      await api<{ id: string }>('/source-versions', {
        method: 'POST',
        body: JSON.stringify({
          source_id: selected.id,
          version_label: label,
          publication_date: optionalFieldValue(data, 'publication_date'),
          valid_from: optionalFieldValue(data, 'valid_from'),
          valid_to: optionalFieldValue(data, 'valid_to'),
          content_hash: await sha256(document),
          storage_key: `sources/${selected.id}/${label}.txt`,
        }),
      });
      await refreshVersions(selected.id);
      form.reset();
    }, 'Versión registrada en revisión.');
  }

  async function addChunk(
    event: SubmitEvent<HTMLFormElement>,
    version: SourceVersion,
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const content = fieldValue(data, 'content');
    await run(async () => {
      await api<{ id: string }>('/source-chunks', {
        method: 'POST',
        body: JSON.stringify({
          source_version_id: version.id,
          chunk_number: version.chunk_count + 1,
          heading: optionalFieldValue(data, 'heading'),
          content,
          token_count: countWords(content),
        }),
      });
      if (selected) await refreshVersions(selected.id);
      form.reset();
    }, 'Fragmento añadido.');
  }

  async function loadChunks(version: SourceVersion) {
    const listed = await api<SourceChunk[]>(
      `/source-versions/${version.id}/chunks`,
    );
    setChunks((previous) => ({ ...previous, [version.id]: listed }));
  }

  async function publish(version: SourceVersion) {
    await run(async () => {
      await api(`/source-versions/${version.id}/publish`, { method: 'POST' });
      await Promise.all([refreshVersions(version.source_id), refreshSources()]);
    }, 'Versión publicada: el asistente ya puede citarla.');
  }

  async function retire(version: SourceVersion) {
    const reason = prompt(
      'Motivo del retiro (queda registrado en el historial):',
    );
    if (!reason || reason.trim().length < 5) return;
    await run(async () => {
      await api(`/source-versions/${version.id}/retire`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason.trim() }),
      });
      await Promise.all([refreshVersions(version.source_id), refreshSources()]);
    }, 'Versión retirada: el asistente deja de citarla.');
  }

  if (loadingSession) {
    return (
      <AppShell eyebrow="Fuentes verificadas" title="Curaduría">
        <div className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  if (!canReview) {
    return (
      <AppShell eyebrow="Fuentes verificadas" title="Curaduría">
        <div className="mx-auto max-w-lg rounded-3xl border bg-card p-8 text-center">
          <ShieldAlert className="mx-auto size-10 text-amber-600" />
          <h2 className="mt-4 font-heading text-xl font-bold">
            No tienes acceso a la curaduría
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Esta sección requiere el permiso <code>source.review</code>.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell eyebrow="Fuentes verificadas" title="Curaduría">
      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <section className="space-y-4">
          <div className="rounded-3xl border bg-card p-6">
            <div className="flex items-start gap-4">
              <span className="grid size-11 place-items-center rounded-xl bg-primary/8 text-primary">
                <BookOpenCheck className="size-5" />
              </span>
              <div>
                <h2 className="font-heading text-lg font-bold">
                  Fuentes registradas
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  El asistente solo cita versiones publicadas.
                </p>
              </div>
            </div>
            {sources.length ? (
              <div className="mt-5 space-y-2">
                {sources.map((source) => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => setSelected(source)}
                    className={`flex w-full items-center gap-3 rounded-2xl border p-4 text-left ${selected?.id === source.id ? 'border-primary bg-primary/5' : ''}`}
                  >
                    <FileText className="size-4 shrink-0 text-primary" />
                    <span className="min-w-0 flex-1">
                      <strong className="block truncate text-sm">
                        {source.title}
                      </strong>
                      <span className="text-xs text-muted-foreground">
                        {source.publisher_name} · {source.topic}
                      </span>
                    </span>
                    <Badge status={source.status} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-5 text-sm text-muted-foreground">
                Aún no hay fuentes registradas.
              </p>
            )}
          </div>

          {selected && (
            <div className="rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">
                Versiones de «{selected.title}»
              </h2>
              {versions.length ? (
                <div className="mt-4 space-y-4">
                  {versions.map((version) => (
                    <article
                      key={version.id}
                      className="rounded-2xl border p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <strong className="text-sm">
                            {version.version_label}
                          </strong>
                          <p className="text-xs text-muted-foreground">
                            {version.chunk_count} fragmento(s)
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge status={version.status} />
                          {canPublish && version.status !== 'PUBLISHED' && (
                            <button
                              type="button"
                              disabled={busy || !version.chunk_count}
                              onClick={() => publish(version)}
                              className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-white disabled:opacity-50"
                            >
                              <Upload className="size-3.5" /> Publicar
                            </button>
                          )}
                          {canPublish && version.status === 'PUBLISHED' && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => retire(version)}
                              className="flex h-9 items-center gap-1.5 rounded-lg border border-red-200 px-3 text-xs font-bold text-red-700 disabled:opacity-50"
                            >
                              <CircleSlash className="size-3.5" /> Retirar
                            </button>
                          )}
                        </div>
                      </div>

                      <form
                        onSubmit={(event) => addChunk(event, version)}
                        className="mt-4 grid gap-3"
                      >
                        <input
                          name="heading"
                          placeholder="Título del fragmento (opcional)"
                          className="h-10 rounded-xl border bg-background px-3 text-sm"
                        />
                        <textarea
                          required
                          name="content"
                          minLength={20}
                          rows={3}
                          placeholder="Texto del fragmento (mínimo 20 caracteres)"
                          className="rounded-xl border bg-background px-3 py-2 text-sm"
                        />
                        <div className="flex gap-2">
                          <button
                            disabled={busy}
                            className="flex h-10 items-center gap-1.5 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50"
                          >
                            <Plus className="size-3.5" /> Añadir fragmento
                          </button>
                          <button
                            type="button"
                            onClick={() => loadChunks(version)}
                            className="h-10 rounded-xl border px-4 text-xs font-bold"
                          >
                            Ver fragmentos
                          </button>
                        </div>
                      </form>

                      {chunks[version.id]?.length ? (
                        <ul className="mt-3 space-y-2">
                          {chunks[version.id].map((chunk) => (
                            <li
                              key={chunk.id}
                              className="rounded-xl bg-muted px-3 py-2 text-xs leading-5"
                            >
                              <strong>
                                {chunk.chunk_number}.{' '}
                                {chunk.heading ?? 'Sin título'}
                              </strong>
                              <p className="mt-1 text-muted-foreground">
                                {chunk.content.slice(0, 180)}
                              </p>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                  Esta fuente todavía no tiene versiones.
                </p>
              )}
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <form
            onSubmit={createSource}
            className="grid gap-4 rounded-3xl border bg-card p-6"
          >
            <h2 className="font-heading text-lg font-bold">Nueva fuente</h2>
            <label className="text-sm font-semibold">
              Institución emisora
              <select required name="publisher_id" className="field">
                <option value="">Selecciona</option>
                {publishers.map((publisher) => (
                  <option key={publisher.id} value={publisher.id}>
                    {publisher.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold">
              Título
              <input required name="title" minLength={2} className="field" />
            </label>
            <label className="text-sm font-semibold">
              Enlace oficial
              <input
                required
                name="canonical_url"
                type="url"
                placeholder="https://..."
                className="field"
              />
            </label>
            <label className="text-sm font-semibold">
              Tema
              <input
                required
                name="topic"
                minLength={2}
                placeholder="formalización, impuestos…"
                className="field"
              />
            </label>
            <label className="text-sm font-semibold">
              Licencia (opcional)
              <input name="license_name" className="field" />
            </label>
            <button
              disabled={busy}
              className="h-11 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50"
            >
              Crear fuente
            </button>
          </form>

          {selected && (
            <form
              onSubmit={createVersion}
              className="grid gap-4 rounded-3xl border bg-card p-6"
            >
              <h2 className="font-heading text-lg font-bold">Nueva versión</h2>
              <p className="text-xs leading-5 text-muted-foreground">
                El texto del documento se usa para calcular su huella SHA-256 y
                detectar cambios entre versiones.
              </p>
              <label className="text-sm font-semibold">
                Etiqueta
                <input
                  required
                  name="version_label"
                  placeholder="2026-01"
                  className="field"
                />
              </label>
              <label className="text-sm font-semibold">
                Fecha de publicación
                <input name="publication_date" type="date" className="field" />
              </label>
              <label className="text-sm font-semibold">
                Vigente desde
                <input name="valid_from" type="date" className="field" />
              </label>
              <label className="text-sm font-semibold">
                Vigente hasta
                <input name="valid_to" type="date" className="field" />
              </label>
              <label className="text-sm font-semibold">
                Texto del documento
                <textarea
                  required
                  name="document"
                  rows={4}
                  className="mt-2 w-full rounded-xl border bg-background px-3 py-2 text-sm font-normal"
                />
              </label>
              <button
                disabled={busy}
                className="h-11 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50"
              >
                Registrar versión
              </button>
            </form>
          )}

          {notice && (
            <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">
              {notice}
            </p>
          )}
          {error && (
            <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {error}
            </p>
          )}
        </aside>
      </div>
    </AppShell>
  );
}
