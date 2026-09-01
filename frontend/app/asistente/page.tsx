'use client';

import { SubmitEvent, useState } from 'react';
import {
  Bot,
  BookOpenCheck,
  ExternalLink,
  LoaderCircle,
  Send,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue } from '../lib/form';

import type { AssistantAnswer } from '../types/api';

export default function AssistantPage() {
  const [history, setHistory] = useState<
    { question: string; result: AssistantAnswer }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const message = fieldValue(data, 'message').trim();
    if (!message) return;
    setLoading(true);
    setError('');
    try {
      const result = await api<AssistantAnswer>('/assistant/query', {
        method: 'POST',
        body: JSON.stringify({ message }),
      });
      setHistory([...history, { question: message, result }]);
      form.reset();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo consultar.',
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <AppShell eyebrow="Orientación con evidencia" title="Asistente Kawsay">
      <div className="grid gap-6 xl:grid-cols-[1fr_310px]">
        <section className="flex min-h-[68vh] flex-col overflow-hidden rounded-3xl border bg-card shadow-sm">
          <div className="border-b bg-[#123d38] p-5 text-white">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-white/12">
                <Bot className="size-5" />
              </span>
              <div>
                <h2 className="font-heading font-bold">
                  Pregunta con confianza
                </h2>
                <p className="text-xs text-white/65">
                  Si falta evidencia, el sistema te lo dirá claramente.
                </p>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-6 overflow-y-auto p-5 sm:p-6">
            {!history.length && (
              <div className="mx-auto max-w-lg py-10 text-center">
                <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary/8 text-primary">
                  <Sparkles />
                </span>
                <h2 className="mt-5 font-heading text-xl font-bold">
                  ¿En qué te puedo orientar?
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Puedes preguntar, por ejemplo: “¿Qué necesito para registrar
                  mi negocio?” o “¿Cómo calculo el precio de un producto?”
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {[
                    'Registro de negocio',
                    'Cómo fijar precios',
                    'Organizar mis gastos',
                  ].map((item) => (
                    <span
                      key={item}
                      className="rounded-full border bg-background px-3 py-2 text-xs font-semibold"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {history.map(({ question, result }, index) => (
              <div key={index} className="space-y-4">
                <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm leading-6 text-white">
                  {question}
                </div>
                <div className="max-w-[92%] rounded-2xl rounded-bl-md bg-muted px-4 py-4">
                  <p className="whitespace-pre-line text-sm leading-6">
                    {result.answer}
                  </p>
                  {result.warning && (
                    <p className="mt-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                      <ShieldAlert className="mt-0.5 size-4 shrink-0" />{' '}
                      {result.warning}
                    </p>
                  )}
                  {result.citations.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="flex items-center gap-2 text-xs font-bold text-primary">
                        <BookOpenCheck className="size-4" /> Fuentes consultadas
                      </p>
                      {result.citations.map((cite) => (
                        <a
                          key={cite.url}
                          href={cite.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-start justify-between gap-3 rounded-xl border bg-card p-3 text-xs hover:border-primary/30"
                        >
                          <span>
                            <strong className="block">
                              {cite.institution}
                            </strong>
                            <span className="mt-1 block text-muted-foreground">
                              {cite.title}{' '}
                              {cite.version_or_date &&
                                `· ${cite.version_or_date}`}
                            </span>
                          </span>
                          <ExternalLink className="size-4 shrink-0 text-primary" />
                        </a>
                      ))}
                    </div>
                  )}
                  <p className="mt-3 text-[10px] text-muted-foreground">
                    Traza: {result.trace_id}
                  </p>
                </div>
              </div>
            ))}
          </div>
          <form onSubmit={submit} className="border-t bg-background p-4">
            <div className="flex gap-3">
              <textarea
                required
                name="message"
                rows={2}
                className="min-h-12 flex-1 resize-none rounded-xl border bg-card px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/25"
                placeholder="Escribe tu pregunta…"
              />
              <button
                disabled={loading}
                className="grid size-12 shrink-0 place-items-center self-end rounded-xl bg-primary text-white disabled:opacity-60"
                aria-label="Enviar pregunta"
              >
                {loading ? (
                  <LoaderCircle className="size-5 animate-spin" />
                ) : (
                  <Send className="size-5" />
                )}
              </button>
            </div>
            {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
          </form>
        </section>
        <aside className="space-y-4">
          <div className="rounded-3xl border bg-card p-5">
            <BookOpenCheck className="size-6 text-emerald-700" />
            <h2 className="mt-4 font-heading font-bold">Cómo funciona</h2>
            <ol className="mt-3 space-y-3 text-sm leading-5 text-muted-foreground">
              <li>
                <strong className="text-foreground">1.</strong> Busca
                información publicada.
              </li>
              <li>
                <strong className="text-foreground">2.</strong> Muestra
                institución y enlace.
              </li>
              <li>
                <strong className="text-foreground">3.</strong> Se abstiene si
                no hay respaldo.
              </li>
            </ol>
          </div>
          <div className="rounded-3xl bg-secondary p-5">
            <ShieldAlert className="size-6 text-secondary-foreground" />
            <h2 className="mt-4 font-heading font-bold">Importante</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              La orientación educativa no reemplaza asesoría legal, tributaria o
              financiera profesional.
            </p>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
