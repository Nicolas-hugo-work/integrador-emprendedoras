'use client';

import { SubmitEvent, useCallback, useEffect, useState } from 'react';
import {
  BookOpenCheck,
  Check,
  CircleSlash,
  FileText,
  Info,
  LoaderCircle,
  Merge,
  Scissors,
  ShieldAlert,
  Trash2,
  Upload,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import {
  type Fragment,
  normalizeSourceUrl,
  splitIntoFragments,
} from '../lib/documents';
import { fieldValue, optionalFieldValue } from '../lib/form';
import { useSession } from '../lib/session';
import type { Publisher, Source, SourceVersion } from '../types/api';

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

function Step({
  number,
  title,
  help,
  done,
  children,
}: {
  number: number;
  title: string;
  help: string;
  done?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-3xl border bg-card p-6">
      <div className="mb-5 flex items-start gap-4">
        <span
          className={`grid size-9 shrink-0 place-items-center rounded-full text-sm font-bold ${done ? 'bg-emerald-600 text-white' : 'bg-primary/10 text-primary'}`}
        >
          {done ? <Check className="size-4" /> : number}
        </span>
        <div>
          <h2 className="font-heading text-lg font-bold">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{help}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

/** Huella del documento, para detectar si cambió respecto de otra versión. */
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

export default function CurationPage() {
  const { has, loading: loadingSession } = useSession();
  const canReview = has('source.review');
  const canPublish = has('source.publish');

  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [selected, setSelected] = useState<Source | null>(null);
  const [versions, setVersions] = useState<SourceVersion[]>([]);
  const [documentText, setDocumentText] = useState('');
  const [fragments, setFragments] = useState<Fragment[] | null>(null);
  const [dropped, setDropped] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const refreshSources = useCallback(async () => {
    setSources(await api<Source[]>('/sources'));
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

  async function crearFuente(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await run(async () => {
      const creada = await api<{ id: string }>('/sources', {
        method: 'POST',
        body: JSON.stringify({
          publisher_id: fieldValue(data, 'publisher_id'),
          title: fieldValue(data, 'title'),
          // Se completa el esquema si falta: antes `www.seprec.gob.bo` se
          // rechazaba sin decir por qué.
          canonical_url: normalizeSourceUrl(fieldValue(data, 'canonical_url')),
          topic: fieldValue(data, 'topic'),
          license_name: optionalFieldValue(data, 'license_name'),
        }),
      });
      await refreshSources();
      const listadas = await api<Source[]>('/sources');
      setSelected(listadas.find((item) => item.id === creada.id) ?? null);
      form.reset();
    }, 'Fuente creada. Ahora carga su documento.');
  }

  function prepararFragmentos() {
    const resultado = splitIntoFragments(documentText);
    setFragments(resultado.fragments);
    setDropped(resultado.duplicatesDropped);
    setNotice(
      resultado.fragments.length
        ? `El documento se dividió en ${resultado.fragments.length} fragmentos. Revísalos antes de guardar.`
        : 'No se pudo dividir el texto: revisa que tenga contenido.',
    );
  }

  function editarFragmento(index: number, content: string) {
    setFragments((current) =>
      current
        ? current.map((item, i) => (i === index ? { ...item, content } : item))
        : current,
    );
  }

  function unirConAnterior(index: number) {
    setFragments((current) => {
      if (!current || index === 0) return current;
      const copia = [...current];
      copia[index - 1] = {
        ...copia[index - 1],
        content: `${copia[index - 1].content} ${copia[index].content}`.trim(),
      };
      copia.splice(index, 1);
      return copia;
    });
  }

  function separarEnDos(index: number) {
    setFragments((current) => {
      if (!current) return current;
      const texto = current[index].content;
      const mitad = texto.indexOf(' ', Math.floor(texto.length / 2));
      if (mitad < 20 || texto.length - mitad < 20) return current;
      const copia = [...current];
      copia.splice(
        index,
        1,
        { ...current[index], content: texto.slice(0, mitad).trim() },
        { content: texto.slice(mitad).trim() },
      );
      return copia;
    });
  }

  function descartar(index: number) {
    setFragments((current) =>
      current ? current.filter((_, i) => i !== index) : current,
    );
  }

  async function guardarDocumento(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || !fragments?.length) return;
    const data = new FormData(event.currentTarget);
    const etiqueta = fieldValue(data, 'version_label');
    await run(async () => {
      const version = await api<{ id: string }>('/source-versions', {
        method: 'POST',
        body: JSON.stringify({
          source_id: selected.id,
          version_label: etiqueta,
          publication_date: optionalFieldValue(data, 'publication_date'),
          valid_from: optionalFieldValue(data, 'valid_from'),
          valid_to: optionalFieldValue(data, 'valid_to'),
          content_hash: await sha256(documentText),
          storage_key: `sources/${selected.id}/${etiqueta}.txt`,
        }),
      });
      // Una sola petición: si algo falla, no queda media carga.
      await api(`/source-versions/${version.id}/chunks`, {
        method: 'POST',
        body: JSON.stringify({
          chunks: fragments.map((fragment) => ({
            heading: fragment.heading ?? null,
            content: fragment.content,
          })),
        }),
      });
      setVersions(
        await api<SourceVersion[]>(`/sources/${selected.id}/versions`),
      );
      setFragments(null);
      setDocumentText('');
      setDropped(0);
    }, 'Documento guardado. Revísalo y publícalo en el paso 3.');
  }

  async function publicar(version: SourceVersion) {
    await run(async () => {
      await api(`/source-versions/${version.id}/publish`, { method: 'POST' });
      setVersions(
        await api<SourceVersion[]>(`/sources/${version.source_id}/versions`),
      );
      await refreshSources();
    }, 'Publicada: el asistente ya puede citarla.');
  }

  async function retirar(version: SourceVersion) {
    const motivo = prompt('Motivo del retiro (queda en el historial):');
    if (!motivo || motivo.trim().length < 5) return;
    await run(async () => {
      await api(`/source-versions/${version.id}/retire`, {
        method: 'POST',
        body: JSON.stringify({ reason: motivo.trim() }),
      });
      setVersions(
        await api<SourceVersion[]>(`/sources/${version.source_id}/versions`),
      );
      await refreshSources();
    }, 'Retirada: el asistente deja de citarla.');
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
      <div className="mx-auto max-w-4xl space-y-6">
        {notice && (
          <p className="rounded-2xl bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
            {notice}
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="rounded-2xl bg-red-50 p-4 text-sm font-semibold text-red-700"
          >
            {error}
          </p>
        )}

        <Step
          number={1}
          title="La fuente"
          help="De dónde viene el documento. Se hace una sola vez por documento oficial; después puedes cargarle nuevas versiones."
          done={Boolean(selected)}
        >
          {sources.length > 0 && (
            <div className="mb-5">
              <p className="mb-2 text-sm font-semibold">
                Continuar con una fuente ya registrada
              </p>
              <div className="space-y-2">
                {sources.map((source) => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => setSelected(source)}
                    className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-left ${selected?.id === source.id ? 'border-primary bg-primary/5' : ''}`}
                  >
                    <FileText className="size-4 shrink-0 text-primary" />
                    <span className="min-w-0 flex-1">
                      <strong className="block truncate text-sm">
                        {source.title}
                      </strong>
                      <span className="text-xs text-muted-foreground">
                        {source.publisher_name}
                      </span>
                    </span>
                    <Badge status={source.status} />
                  </button>
                ))}
              </div>
            </div>
          )}

          <details
            className="rounded-2xl border p-4"
            open={sources.length === 0}
          >
            <summary className="cursor-pointer text-sm font-semibold">
              Registrar una fuente nueva
            </summary>
            <form
              onSubmit={crearFuente}
              className="mt-4 grid gap-4 sm:grid-cols-2"
            >
              <label className="text-sm font-semibold">
                Institución que la publica
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
                Título del documento
                <input
                  required
                  name="title"
                  minLength={2}
                  placeholder="Guía de registro de comercio"
                  className="field"
                />
              </label>
              <label className="text-sm font-semibold sm:col-span-2">
                Enlace a la página oficial
                <input
                  required
                  name="canonical_url"
                  placeholder="www.seprec.gob.bo/guia"
                  className="field"
                />
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  Puedes pegarlo sin <code>https://</code>: se completa solo. Es
                  el enlace que verá la emprendedora junto a la cita.
                </span>
              </label>
              <label className="text-sm font-semibold">
                Tema
                <input
                  required
                  name="topic"
                  minLength={2}
                  placeholder="formalización"
                  className="field"
                />
              </label>
              <label className="text-sm font-semibold">
                Licencia (opcional)
                <input name="license_name" className="field" />
              </label>
              <button
                disabled={busy}
                className="h-11 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50 sm:col-span-2"
              >
                Registrar fuente
              </button>
            </form>
          </details>
        </Step>

        <Step
          number={2}
          title="El documento"
          help="Pega el texto una sola vez. Se divide solo en fragmentos, que son las piezas que el asistente puede citar."
          done={versions.length > 0}
        >
          {!selected ? (
            <p className="flex gap-2 rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
              <Info className="mt-0.5 size-4 shrink-0" />
              Elige o registra una fuente en el paso 1 para continuar.
            </p>
          ) : (
            <form onSubmit={guardarDocumento} className="grid gap-4">
              <label className="text-sm font-semibold">
                Cómo se identifica esta versión
                <input
                  required
                  name="version_label"
                  placeholder="Gestión 2026"
                  className="field"
                />
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  Lo que distingue esta versión de otra del mismo documento: el
                  año, el número de resolución o la fecha de la edición.
                </span>
              </label>

              <div className="grid gap-4 sm:grid-cols-3">
                <label className="text-sm font-semibold">
                  Fecha de publicación
                  <input
                    name="publication_date"
                    type="date"
                    className="field"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Vigente desde
                  <input name="valid_from" type="date" className="field" />
                </label>
                <label className="text-sm font-semibold">
                  Vigente hasta
                  <input name="valid_to" type="date" className="field" />
                </label>
              </div>

              <label className="text-sm font-semibold">
                Texto del documento
                <textarea
                  required
                  rows={8}
                  value={documentText}
                  onChange={(event) => setDocumentText(event.target.value)}
                  placeholder="Pega aquí el texto completo, tal como está en la página oficial."
                  className="mt-2 w-full rounded-xl border bg-background px-3 py-2 text-sm font-normal"
                />
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  Se guarda una huella del texto para poder detectar más
                  adelante si el documento cambió respecto de esta versión.
                </span>
              </label>

              <button
                type="button"
                disabled={busy || documentText.trim().length < 20}
                onClick={prepararFragmentos}
                className="h-11 rounded-xl border px-5 text-sm font-bold disabled:opacity-50"
              >
                Dividir en fragmentos
              </button>

              {fragments && (
                <div className="rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <strong className="text-sm">
                      {fragments.length} fragmento(s)
                    </strong>
                    {dropped > 0 && (
                      <span className="text-xs text-muted-foreground">
                        Se descartaron {dropped} fragmento(s) repetidos: el
                        sistema no admite dos idénticos en la misma versión.
                      </span>
                    )}
                  </div>

                  <ul className="mt-4 space-y-3">
                    {fragments.map((fragment, index) => (
                      <li key={index} className="rounded-xl bg-muted/50 p-3">
                        {fragment.heading && (
                          <p className="mb-1 text-xs font-bold">
                            {fragment.heading}
                          </p>
                        )}
                        <textarea
                          rows={3}
                          value={fragment.content}
                          onChange={(event) =>
                            editarFragmento(index, event.target.value)
                          }
                          className="w-full rounded-lg border bg-background px-3 py-2 text-xs leading-5"
                        />
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={index === 0}
                            onClick={() => unirConAnterior(index)}
                            className="flex h-8 items-center gap-1 rounded-lg border px-2 text-xs font-bold disabled:opacity-40"
                          >
                            <Merge className="size-3" /> Unir con el anterior
                          </button>
                          <button
                            type="button"
                            onClick={() => separarEnDos(index)}
                            className="flex h-8 items-center gap-1 rounded-lg border px-2 text-xs font-bold"
                          >
                            <Scissors className="size-3" /> Separar en dos
                          </button>
                          <button
                            type="button"
                            onClick={() => descartar(index)}
                            className="flex h-8 items-center gap-1 rounded-lg border border-red-200 px-2 text-xs font-bold text-red-700"
                          >
                            <Trash2 className="size-3" /> Descartar
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>

                  <button
                    disabled={busy || !fragments.length}
                    className="mt-4 h-11 w-full rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50"
                  >
                    Guardar documento y sus {fragments.length} fragmentos
                  </button>
                </div>
              )}
            </form>
          )}
        </Step>

        <Step
          number={3}
          title="Revisar y publicar"
          help="Mientras no esté publicada, el asistente no puede citar la versión."
          done={versions.some((version) => version.status === 'PUBLISHED')}
        >
          {!selected ? (
            <p className="flex gap-2 rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
              <Info className="mt-0.5 size-4 shrink-0" />
              Elige una fuente para ver sus versiones.
            </p>
          ) : versions.length ? (
            <div className="space-y-3">
              {versions.map((version) => (
                <article key={version.id} className="rounded-2xl border p-4">
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
                          onClick={() => publicar(version)}
                          className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-white disabled:opacity-50"
                        >
                          <Upload className="size-3.5" /> Publicar
                        </button>
                      )}
                      {canPublish && version.status === 'PUBLISHED' && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => retirar(version)}
                          className="flex h-9 items-center gap-1.5 rounded-lg border border-red-200 px-3 text-xs font-bold text-red-700 disabled:opacity-50"
                        >
                          <CircleSlash className="size-3.5" /> Retirar
                        </button>
                      )}
                    </div>
                  </div>
                  {!version.chunk_count && (
                    <p className="mt-3 flex gap-2 text-xs leading-5 text-muted-foreground">
                      <Info className="mt-0.5 size-3.5 shrink-0" />
                      No se puede publicar sin fragmentos: vuelve al paso 2 y
                      carga el texto del documento.
                    </p>
                  )}
                  {!canPublish && (
                    <p className="mt-3 text-xs leading-5 text-muted-foreground">
                      Publicar y retirar requieren el permiso{' '}
                      <code>source.publish</code>.
                    </p>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="flex gap-2 rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
              <BookOpenCheck className="mt-0.5 size-4 shrink-0" />
              Esta fuente todavía no tiene ninguna versión cargada.
            </p>
          )}
        </Step>
      </div>
    </AppShell>
  );
}
