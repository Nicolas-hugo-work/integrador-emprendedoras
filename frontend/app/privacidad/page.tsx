'use client';

import { useEffect, useState } from 'react';
import {
  Database,
  Download,
  LoaderCircle,
  LockKeyhole,
  Mic,
  Share2,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api, clearTokens } from '../lib/api';
import type { ConsentStatus } from '../types/api';

/** Texto propio para las finalidades conocidas; el resto usa el del backend. */
const COPY: Record<string, { icon: typeof Mic; description: string }> = {
  AUDIO: {
    icon: Mic,
    description:
      'Permite transcribir notas de voz. El archivo temporal se elimina tras confirmar la transcripción o dentro de 24 horas.',
  },
  RESEARCH: {
    icon: Database,
    description:
      'Autoriza el uso de métricas seudonimizadas del piloto. Nunca incluye tu nombre ni conversaciones completas.',
  },
  SECONDARY_USE: {
    icon: Share2,
    description:
      'Autoriza usos adicionales descritos por separado. Puedes retirarlo en cualquier momento.',
  },
};

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function PrivacyPage() {
  const [consents, setConsents] = useState<ConsentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const listed = await api<ConsentStatus[]>('/consents');
        if (alive) setConsents(listed);
      } catch (reason) {
        if (alive)
          setError(describe(reason, 'No se pudieron cargar tus preferencias.'));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function decide(consent: ConsentStatus, granted: boolean) {
    setError('');
    setMessage('');
    try {
      await api('/consents', {
        method: 'POST',
        body: JSON.stringify({
          purpose_code: consent.purpose_code,
          version: consent.version ?? '1.0',
          decision: granted ? 'GRANTED' : 'WITHDRAWN',
        }),
      });
      // Se relee del servidor: lo que se muestra es lo que quedó guardado.
      setConsents(await api<ConsentStatus[]>('/consents'));
      setMessage('Tu preferencia quedó guardada.');
    } catch (reason) {
      setError(describe(reason, 'No se pudo guardar.'));
    }
  }

  async function deleteAccount() {
    const confirmed = confirm(
      'Tu cuenta se desactivará ahora y sus datos se purgarán en un máximo de 30 días. ¿Continuar?',
    );
    if (!confirmed) return;
    try {
      await api('/privacy/deletion', {
        method: 'POST',
        body: JSON.stringify({ confirmation: 'ELIMINAR MI CUENTA' }),
      });
      clearTokens();
      window.location.href = '/login';
    } catch (reason) {
      setError(describe(reason, 'No se pudo solicitar.'));
    }
  }

  async function requestExport() {
    setError('');
    setMessage('');
    setExporting(true);
    try {
      // La copia se genera en el momento de descargarla: no hay un archivo
      // esperando en ninguna parte.
      const solicitud = await api<{ request_id: string }>('/privacy/export', {
        method: 'POST',
      });
      const contenido = await api<unknown>(
        `/privacy/export/${solicitud.request_id}`,
      );
      const enlace = document.createElement('a');
      enlace.href = URL.createObjectURL(
        new Blob([JSON.stringify(contenido, null, 2)], {
          type: 'application/json',
        }),
      );
      enlace.download = `kawsay-mis-datos-${new Date().toISOString().slice(0, 10)}.json`;
      enlace.click();
      URL.revokeObjectURL(enlace.href);
      setMessage('Tu copia se descargó en formato JSON.');
    } catch (reason) {
      setError(describe(reason, 'No se pudo preparar la copia.'));
    } finally {
      setExporting(false);
    }
  }

  const optional = consents.filter((consent) => !consent.is_required);

  return (
    <AppShell
      eyebrow="Tus datos, tus decisiones"
      title="Privacidad y consentimientos"
    >
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <section className="space-y-4">
          <div className="rounded-3xl border bg-card p-6">
            <div className="flex gap-4">
              <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
                <ShieldCheck />
              </span>
              <div>
                <h2 className="font-heading text-xl font-bold">
                  Control de consentimientos
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Retirar un permiso desactiva esa función, pero no cierra tu
                  cuenta.
                </p>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="grid min-h-40 place-items-center rounded-3xl border bg-card">
              <LoaderCircle className="animate-spin text-primary" />
            </div>
          ) : (
            optional.map((consent) => {
              const copy = COPY[consent.purpose_code];
              const Icon = copy?.icon ?? ShieldCheck;
              return (
                <article
                  key={consent.purpose_code}
                  className="flex gap-4 rounded-3xl border bg-card p-6"
                >
                  <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/8 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="max-w-xl">
                        <h3 className="font-bold">{consent.name}</h3>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {copy?.description ?? consent.withdrawal_effect}
                        </p>
                        <p className="mt-2 text-xs text-muted-foreground">
                          {consent.decision === null
                            ? 'Todavía no has decidido sobre esta finalidad.'
                            : `Al retirarlo: ${consent.withdrawal_effect.toLowerCase()}`}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => decide(consent, !consent.allowed)}
                        role="switch"
                        aria-checked={consent.allowed}
                        aria-label={consent.name}
                        className={`relative h-7 w-12 shrink-0 rounded-full transition ${consent.allowed ? 'bg-primary' : 'bg-muted-foreground/30'}`}
                      >
                        <span
                          className={`absolute top-1 size-5 rounded-full bg-white transition ${consent.allowed ? 'left-6' : 'left-1'}`}
                        />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })
          )}

          {message && (
            <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">
              {message}
            </p>
          )}
          {error && (
            <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <div className="rounded-3xl border border-red-200 bg-card p-6">
            <div className="flex items-start gap-4">
              <Trash2 className="mt-1 size-5 text-red-700" />
              <div className="flex-1">
                <h2 className="font-bold text-red-800">Eliminar mi cuenta</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Se desactiva inmediatamente y la purga física se programa
                  dentro de 30 días.
                </p>
                <button
                  type="button"
                  onClick={deleteAccount}
                  className="mt-4 rounded-xl border border-red-200 px-4 py-2 text-sm font-bold text-red-700 hover:bg-red-50"
                >
                  Solicitar eliminación
                </button>
              </div>
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-3xl bg-primary p-6 text-white">
            <LockKeyhole className="size-7" />
            <h2 className="mt-5 font-heading text-xl font-bold">
              Protección incorporada
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-5 text-white/70">
              <li>Contenido sensible cifrado</li>
              <li>Acceso aislado por usuaria</li>
              <li>Auditoría seudonimizada</li>
              <li>Sin entrenamiento por defecto</li>
            </ul>
          </div>
          <button
            type="button"
            onClick={requestExport}
            disabled={exporting}
            className="flex w-full items-center gap-3 rounded-2xl border bg-card p-4 text-left text-sm font-bold disabled:opacity-60"
          >
            {exporting ? (
              <LoaderCircle className="size-5 animate-spin text-primary" />
            ) : (
              <Download className="size-5 text-primary" />
            )}
            {exporting
              ? 'Preparando tu copia…'
              : 'Descargar copia de mis datos'}
          </button>
        </aside>
      </div>
    </AppShell>
  );
}
