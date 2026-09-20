'use client';

import { SubmitEvent, useEffect, useState } from 'react';
import { CheckCircle2, ClipboardList, LoaderCircle } from 'lucide-react';
import { useOffline } from 'next/offline';

import { AppShell } from '../components/app-shell';
import {
  api,
  apiCached,
  isNetworkError,
  OFFLINE_WRITE_ERROR,
} from '../lib/api';
import { describeStaleness } from '../lib/staleness';
import type {
  Business,
  DiagnosticQuestion,
  DiagnosticSession,
  FormalizationRoute,
} from '../types/api';

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function DiagnosticPage() {
  const offline = useOffline();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [questions, setQuestions] = useState<DiagnosticQuestion[]>([]);
  const [businessId, setBusinessId] = useState('');
  const [session, setSession] = useState<DiagnosticSession | null>(null);
  const [route, setRoute] = useState<FormalizationRoute | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [bootFailed, setBootFailed] = useState(false);
  const [stale, setStale] = useState(false);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const [listed, asked] = await Promise.all([
          apiCached<Business[]>('/businesses'),
          apiCached<DiagnosticQuestion[]>('/diagnostic-questions'),
        ]);
        if (!alive) return;
        setBusinesses(listed.data);
        setQuestions(asked.data);
        setStale(listed.stale || asked.stale);
        setFetchedAt(listed.fetchedAt);
        if (listed.data[0]) setBusinessId(listed.data[0].id);
      } catch (reason) {
        if (alive) {
          setBootFailed(true);
          setError(describe(reason, 'No se pudo cargar.'));
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!businessId) return;
    let alive = true;
    void (async () => {
      try {
        const listed = await apiCached<FormalizationRoute[]>(
          `/formalization-routes?business_id=${businessId}`,
        );
        if (!alive) return;
        setRoute(listed.data[0] ?? null);
        if (listed.stale) setStale(true);
      } catch {
        if (alive) setRoute(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [businessId]);

  async function start(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (offline) {
      setError(OFFLINE_WRITE_ERROR);
      return;
    }
    setSaving(true);
    setError('');
    try {
      const created = await api<DiagnosticSession>('/diagnostic-sessions', {
        method: 'POST',
        body: JSON.stringify({ business_id: businessId }),
      });
      setSession(created);
      setAnswers({});
    } catch (reason) {
      setError(
        isNetworkError(reason)
          ? OFFLINE_WRITE_ERROR
          : describe(reason, 'No se pudo empezar.'),
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveAll() {
    if (!session) return;
    if (offline) {
      setError(OFFLINE_WRITE_ERROR);
      return;
    }
    setSaving(true);
    setError('');
    try {
      let current = session;
      for (const question of questions) {
        const text = (answers[question.code] ?? '').trim();
        if (!text) {
          setError('Responde las tres preguntas para armar la ruta.');
          setSaving(false);
          return;
        }
        current = await api<DiagnosticSession>(
          `/diagnostic-sessions/${session.id}/answers`,
          {
            method: 'PUT',
            body: JSON.stringify({
              question_code: question.code,
              answer_text: text,
            }),
          },
        );
      }
      const built = await api<FormalizationRoute>(
        `/diagnostic-sessions/${session.id}/complete`,
        { method: 'POST' },
      );
      setSession(current);
      setRoute(built);
    } catch (reason) {
      setError(
        isNetworkError(reason)
          ? OFFLINE_WRITE_ERROR
          : describe(reason, 'No se pudo guardar.'),
      );
    } finally {
      setSaving(false);
    }
  }

  async function completeStep(stepId: string) {
    if (offline) {
      setError(OFFLINE_WRITE_ERROR);
      return;
    }
    setError('');
    try {
      setRoute(
        await api<FormalizationRoute>(`/formalization-steps/${stepId}/complete`, {
          method: 'POST',
        }),
      );
    } catch (reason) {
      setError(
        isNetworkError(reason)
          ? OFFLINE_WRITE_ERROR
          : describe(reason, 'No se pudo marcar el paso.'),
      );
    }
  }

  return (
    <AppShell eyebrow="Formalización" title="Diagnóstico">
      {loading ? (
        <div aria-live="polite" className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
          <span className="sr-only">Cargando diagnóstico</span>
        </div>
      ) : bootFailed && !businesses.length ? (
        <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error || 'No se pudo cargar.'}
        </p>
      ) : !businesses.length ? (
        <p className="rounded-3xl border bg-card p-8 text-sm text-muted-foreground">
          Primero registra tu emprendimiento.
        </p>
      ) : (
        <div className="space-y-6">
          {stale && (
            <p className="text-sm font-medium text-amber-800">
              {describeStaleness(fetchedAt)}
            </p>
          )}
          <form onSubmit={start} className="rounded-3xl border bg-card p-6">
            <label className="text-sm font-semibold">
              Negocio
              <select
                value={businessId}
                onChange={(event) => setBusinessId(event.target.value)}
                className="mt-2 h-12 w-full rounded-xl border bg-background px-3"
              >
                {businesses.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              disabled={saving || offline}
              className="mt-4 flex h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-60"
            >
              {saving && <LoaderCircle className="size-4 animate-spin" />}
              Empezar diagnóstico
            </button>
          </form>

          {session && session.status === 'IN_PROGRESS' && (
            <section className="space-y-4 rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">
                Cuestionario {session.questionnaire_version}
              </h2>
              {questions.map((question) => (
                <label key={question.code} className="block text-sm font-semibold">
                  {question.prompt}
                  <textarea
                    value={answers[question.code] ?? ''}
                    onChange={(event) =>
                      setAnswers((current) => ({
                        ...current,
                        [question.code]: event.target.value,
                      }))
                    }
                    rows={3}
                    className="mt-2 w-full rounded-xl border bg-background px-3 py-2 font-normal"
                  />
                </label>
              ))}
              <button
                type="button"
                disabled={saving || offline}
                onClick={() => void saveAll()}
                className="flex h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-60"
              >
                Armar mi ruta
              </button>
            </section>
          )}

          {route && (
            <section className="space-y-3 rounded-3xl border bg-card p-6">
              <div className="flex items-center gap-2">
                <ClipboardList className="size-5 text-primary" />
                <h2 className="font-heading text-lg font-bold">
                  Ruta de formalización
                </h2>
              </div>
              <p className="text-sm text-muted-foreground">
                Pasos plantilla con fuentes publicadas cuando hay. No es un
                trámite hecho por una máquina.
              </p>
              {route.steps.map((step) => (
                <article key={step.id} className="rounded-2xl border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <strong>
                        {step.step_number}. {step.title}
                      </strong>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {step.description}
                      </p>
                    </div>
                    {step.completed_at ? (
                      <CheckCircle2 className="size-5 shrink-0 text-emerald-600" />
                    ) : (
                      <button
                        type="button"
                        disabled={offline}
                        onClick={() => void completeStep(step.id)}
                        className="shrink-0 rounded-lg border px-3 py-1 text-xs font-bold"
                      >
                        Hecho
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </section>
          )}

          {error && (
            <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>
          )}
        </div>
      )}
    </AppShell>
  );
}
