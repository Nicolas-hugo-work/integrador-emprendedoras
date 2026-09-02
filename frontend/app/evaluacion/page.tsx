'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  ArrowRight,
  CircleCheck,
  CircleX,
  FlaskConical,
  LoaderCircle,
  Play,
  ShieldAlert,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import {
  asPercent,
  compareRuns,
  runRates,
  summarize,
  type CaseComparison,
} from '../lib/evaluation';
import { useSession } from '../lib/session';
import type {
  EvaluationCase,
  EvaluationRun,
  EvaluationRunDetail,
  EvaluationSet,
} from '../types/api';

const CATEGORY_LABEL: Record<string, string> = {
  FORMALIZATION: 'Formalización',
  FINANCE: 'Finanzas',
  MARKETING: 'Mercadeo',
  SAFETY: 'Seguridad',
  INJECTION: 'Inyección',
  PII: 'Datos personales',
  NO_EVIDENCE: 'Sin evidencia',
};

const CHANGE_STYLE: Record<string, string> = {
  mejora: 'bg-emerald-50 text-emerald-700',
  retroceso: 'bg-red-50 text-red-700',
  igual: 'bg-muted text-muted-foreground',
  incomparable: 'bg-amber-50 text-amber-800',
};

const RATE_ROWS = [
  ['passed', 'Casos que pasan'],
  ['recall', 'Recuperación'],
  ['cited', 'Respuestas con cita'],
  ['warned', 'Con advertencia normativa'],
  ['abstained', 'Abstenciones'],
] as const;

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

function Verdict({ passed }: { passed: boolean }) {
  return passed ? (
    <span className="inline-flex items-center gap-1 text-emerald-700">
      <CircleCheck className="size-4" /> pasa
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-red-700">
      <CircleX className="size-4" /> falla
    </span>
  );
}

export default function EvaluationPage() {
  const { has, loading: loadingSession } = useSession();
  const canRead = has('source.review') || has('audit.read');
  const canRun = has('source.review');

  const [sets, setSets] = useState<EvaluationSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<string>('');
  const [cases, setCases] = useState<EvaluationCase[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [before, setBefore] = useState<EvaluationRunDetail | null>(null);
  const [after, setAfter] = useState<EvaluationRunDetail | null>(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    if (!canRead) return;
    let alive = true;
    void (async () => {
      try {
        const listed = await api<EvaluationSet[]>('/evaluation/sets');
        if (!alive) return;
        setSets(listed);
        setSelectedSet((current) => current || (listed[0]?.id ?? ''));
      } catch (reason) {
        if (alive) setError(describe(reason, 'No se pudieron cargar los conjuntos.'));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [canRead]);

  const loadSet = useCallback(async (setId: string) => {
    const [listedCases, listedRuns] = await Promise.all([
      api<EvaluationCase[]>(`/evaluation/sets/${setId}/cases`),
      api<EvaluationRun[]>(`/evaluation/runs?evaluation_set_id=${setId}`),
    ]);
    return { listedCases, listedRuns };
  }, []);

  useEffect(() => {
    if (!selectedSet) return;
    let alive = true;
    void (async () => {
      try {
        const { listedCases, listedRuns } = await loadSet(selectedSet);
        if (!alive) return;
        setCases(listedCases);
        setRuns(listedRuns);
        setBefore(null);
        setAfter(null);
      } catch (reason) {
        if (alive) setError(describe(reason, 'No se pudo cargar el conjunto.'));
      }
    })();
    return () => {
      alive = false;
    };
  }, [selectedSet, loadSet]);

  async function execute() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const run = await api<EvaluationRunDetail>(
        `/evaluation/sets/${selectedSet}/runs`,
        { method: 'POST' },
      );
      const { listedRuns } = await loadSet(selectedSet);
      setRuns(listedRuns);
      setAfter(run);
      setNotice(
        `Tanda ejecutada con ${run.model_name} ${run.model_version}: ` +
          `${run.passed_cases} de ${run.total_cases} casos pasan.`,
      );
    } catch (reason) {
      setError(describe(reason, 'No se pudo ejecutar la tanda.'));
    } finally {
      setBusy(false);
    }
  }

  async function pick(runId: string, slot: 'before' | 'after') {
    setError('');
    try {
      const detail = await api<EvaluationRunDetail>(`/evaluation/runs/${runId}`);
      if (slot === 'before') setBefore(detail);
      else setAfter(detail);
    } catch (reason) {
      setError(describe(reason, 'No se pudo cargar la corrida.'));
    }
  }

  if (loadingSession || loading) {
    return (
      <AppShell eyebrow="Medición del asistente" title="Evaluación">
        <div className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  if (!canRead) {
    return (
      <AppShell eyebrow="Medición del asistente" title="Evaluación">
        <div className="mx-auto max-w-lg rounded-3xl border bg-card p-8 text-center">
          <ShieldAlert className="mx-auto size-10 text-amber-600" />
          <h2 className="mt-4 font-heading text-xl font-bold">
            No tienes acceso a la evaluación
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Esta sección requiere <code>source.review</code> o{' '}
            <code>audit.read</code>.
          </p>
        </div>
      </AppShell>
    );
  }

  const comparisons: CaseComparison[] =
    before && after ? compareRuns(before, after) : [];

  return (
    <AppShell eyebrow="Medición del asistente" title="Evaluación">
      <div className="space-y-6">
        {notice && (
          <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">
            {notice}
          </p>
        )}
        {error && (
          <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="rounded-3xl border bg-card p-6">
          <div className="flex items-start gap-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/8 text-primary">
              <FlaskConical className="size-5" />
            </span>
            <div>
              <h2 className="font-heading text-lg font-bold">
                Qué mide este banco
              </h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                No mide si el asistente escribe bien. Mide las tres cosas que el
                proyecto promete: que cite siempre, que advierta cuando la
                respuesta es normativa y que se abstenga cuando no hay
                evidencia. Cada caso lleva una categoría, y de la categoría sale
                lo que se le exige a la respuesta.
              </p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Ejecutar una tanda no crea conversaciones ni mensajes: recorre
                el mismo camino que atiende a las usuarias, sin escribir nada de
                lo que ese camino escribe.
              </p>
            </div>
          </div>
        </div>

        {sets.length === 0 ? (
          <section className="rounded-3xl border bg-card p-6">
            <h2 className="font-heading text-lg font-bold">
              Todavía no hay conjuntos
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Un conjunto reúne los casos con los que se mide al asistente. Se
              siembra uno de base con{' '}
              <code>python -m scripts.seed_evaluation_set</code> en el backend, y
              desde ahí se le pueden añadir casos.
            </p>
          </section>
        ) : (
          <>
            <section className="rounded-3xl border bg-card p-6">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <label className="text-sm font-semibold">
                  Conjunto
                  <select
                    value={selectedSet}
                    onChange={(event) => setSelectedSet(event.target.value)}
                    className="field mt-1 block min-w-72"
                  >
                    {sets.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name} · v{item.version}
                      </option>
                    ))}
                  </select>
                </label>
                {canRun && (
                  <button
                    type="button"
                    onClick={execute}
                    disabled={busy || cases.length === 0}
                    className="inline-flex h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-40"
                  >
                    {busy ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : (
                      <Play className="size-4" />
                    )}
                    Ejecutar tanda
                  </button>
                )}
              </div>
              {!canRun && (
                <p className="mt-4 text-sm text-muted-foreground">
                  Puedes leer las corridas y compararlas. Ejecutar una tanda
                  requiere <code>source.review</code>.
                </p>
              )}
            </section>

            <section className="rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">
                Casos del conjunto ({cases.length})
              </h2>
              {cases.length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  Este conjunto no tiene casos, así que no hay nada que
                  ejecutar.
                </p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-bold">Código</th>
                        <th className="py-3 pr-4 font-bold">Categoría</th>
                        <th className="py-3 pr-4 font-bold">Consulta</th>
                        <th className="py-3 font-bold">Qué se le exige</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {cases.map((item) => (
                        <tr key={item.id}>
                          <td className="py-3 pr-4 font-mono text-xs font-semibold">
                            {item.case_code}
                          </td>
                          <td className="py-3 pr-4">
                            <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold">
                              {CATEGORY_LABEL[item.category] ?? item.category}
                            </span>
                          </td>
                          <td className="py-3 pr-4">{item.prompt}</td>
                          <td className="py-3 text-muted-foreground">
                            {item.expected_behavior}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">
                Corridas ({runs.length})
              </h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Elige dos para compararlas: una como <strong>antes</strong> y
                otra como <strong>después</strong>. Comparar corridas de
                distinta versión del modelo es el punto de todo esto.
              </p>
              {runs.length === 0 ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  Todavía no se ejecutó ninguna tanda sobre este conjunto.
                </p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-bold">Fecha</th>
                        <th className="py-3 pr-4 font-bold">Recuperación</th>
                        <th className="py-3 pr-4 font-bold">Resultado</th>
                        <th className="py-3 font-bold">Comparar como</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {runs.map((item) => (
                        <tr key={item.id}>
                          <td className="py-3 pr-4 whitespace-nowrap text-muted-foreground">
                            {new Date(item.created_at).toLocaleString('es-BO')}
                          </td>
                          <td className="py-3 pr-4 font-mono text-xs">
                            {item.model_name} {item.model_version}
                          </td>
                          <td className="py-3 pr-4 font-semibold">
                            {item.passed_cases} / {item.total_cases}
                          </td>
                          <td className="py-3">
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => pick(item.id, 'before')}
                                aria-label={`Usar la corrida del ${new Date(item.created_at).toLocaleString('es-BO')} como antes`}
                                className={`rounded-lg border px-3 py-1.5 text-xs font-bold ${
                                  before?.id === item.id
                                    ? 'border-primary bg-primary/8 text-primary'
                                    : ''
                                }`}
                              >
                                Antes
                              </button>
                              <button
                                type="button"
                                onClick={() => pick(item.id, 'after')}
                                aria-label={`Usar la corrida del ${new Date(item.created_at).toLocaleString('es-BO')} como después`}
                                className={`rounded-lg border px-3 py-1.5 text-xs font-bold ${
                                  after?.id === item.id
                                    ? 'border-primary bg-primary/8 text-primary'
                                    : ''
                                }`}
                              >
                                Después
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {before && after && (
              <section className="rounded-3xl border bg-card p-6">
                <h2 className="font-heading text-lg font-bold">
                  {before.model_version}{' '}
                  <ArrowRight className="inline size-4" />{' '}
                  {after.model_version}
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {summarize(comparisons)}
                </p>

                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[480px] text-left text-sm">
                    <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-bold">Medida</th>
                        <th className="py-3 pr-4 font-bold">
                          Antes ({before.model_version})
                        </th>
                        <th className="py-3 font-bold">
                          Después ({after.model_version})
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {RATE_ROWS.map(([key, label]) => {
                        const antes = runRates(before.results)[key];
                        const despues = runRates(after.results)[key];
                        return (
                          <tr key={key}>
                            <td className="py-3 pr-4 font-semibold">{label}</td>
                            <td className="py-3 pr-4 tabular-nums">
                              {asPercent(antes)}
                            </td>
                            <td
                              className={`py-3 tabular-nums font-bold ${
                                despues > antes
                                  ? 'text-emerald-700'
                                  : despues < antes
                                    ? 'text-red-700'
                                    : ''
                              }`}
                            >
                              {asPercent(despues)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="mt-6 overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-bold">Caso</th>
                        <th className="py-3 pr-4 font-bold">Categoría</th>
                        <th className="py-3 pr-4 font-bold">Antes</th>
                        <th className="py-3 pr-4 font-bold">Después</th>
                        <th className="py-3 pr-4 font-bold">Recuperación</th>
                        <th className="py-3 font-bold">Cambio</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {comparisons.map((row) => (
                        <tr key={row.case_code}>
                          <td className="py-3 pr-4 font-mono text-xs font-semibold">
                            {row.case_code}
                          </td>
                          <td className="py-3 pr-4 text-muted-foreground">
                            {CATEGORY_LABEL[row.category] ?? row.category}
                          </td>
                          <td className="py-3 pr-4">
                            {row.before ? (
                              <Verdict passed={row.before.passed} />
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="py-3 pr-4">
                            {row.after ? (
                              <Verdict passed={row.after.passed} />
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="py-3 pr-4 tabular-nums text-muted-foreground">
                            {asPercent(row.before?.retrieval_recall ?? 0)} →{' '}
                            {asPercent(row.after?.retrieval_recall ?? 0)}
                          </td>
                          <td className="py-3">
                            <span
                              className={`rounded-full px-2.5 py-1 text-xs font-bold ${CHANGE_STYLE[row.change]}`}
                            >
                              {row.change}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {after && !before && (
              <section className="rounded-3xl border bg-card p-6">
                <h2 className="font-heading text-lg font-bold">
                  Última corrida
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {after.passed_cases} de {after.total_cases} casos pasan.
                  Elige una segunda corrida como «antes» para ver qué cambió.
                </p>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4 font-bold">Caso</th>
                        <th className="py-3 pr-4 font-bold">Resultado</th>
                        <th className="py-3 pr-4 font-bold">Recuperación</th>
                        <th className="py-3 font-bold">Observación</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {after.results.map((row) => (
                        <tr key={row.case_id}>
                          <td className="py-3 pr-4 font-mono text-xs font-semibold">
                            {row.case_code}
                          </td>
                          <td className="py-3 pr-4">
                            <Verdict passed={row.passed} />
                          </td>
                          <td className="py-3 pr-4 tabular-nums text-muted-foreground">
                            {asPercent(row.retrieval_recall)}
                          </td>
                          <td className="py-3 text-muted-foreground">
                            {row.notes}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
