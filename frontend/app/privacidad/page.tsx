'use client';

import { useState } from 'react';
import {
  Database,
  Download,
  LockKeyhole,
  Mic,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { AppShell } from '../components/app-shell';
import { api, clearTokens } from '../lib/api';

export default function PrivacyPage() {
  const [audio, setAudio] = useState(false);
  const [research, setResearch] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  async function consent(code: 'AUDIO' | 'RESEARCH', granted: boolean) {
    setError('');
    try {
      await api('/consents', {
        method: 'POST',
        body: JSON.stringify({
          purpose_code: code,
          version: '1.0',
          decision: granted ? 'GRANTED' : 'WITHDRAWN',
        }),
      });
      setMessage('Tu preferencia quedó guardada.');
      if (code === 'AUDIO') {
        setAudio(granted);
      } else {
        setResearch(granted);
      }
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo guardar.',
      );
    }
  }
  async function deleteAccount() {
    if (
      !confirm(
        'Tu cuenta se desactivará ahora y sus datos se purgarán en un máximo de 30 días. ¿Continuar?',
      )
    )
      return;
    try {
      await api('/privacy/deletion', {
        method: 'POST',
        body: JSON.stringify({ confirmation: 'ELIMINAR MI CUENTA' }),
      });
      clearTokens();
      window.location.href = '/login';
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo solicitar.',
      );
    }
  }
  async function requestExport() {
    setError('');
    try {
      await api('/privacy/export', { method: 'POST' });
      setMessage('Solicitud recibida. Prepararemos una copia en formato JSON.');
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo solicitar.',
      );
    }
  }
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
          {[
            {
              title: 'Uso temporal de audio',
              description:
                'Permite transcribir notas de voz. El archivo temporal se elimina tras confirmar la transcripción o dentro de 24 horas.',
              value: audio,
              icon: Mic,
              action: (v: boolean) => consent('AUDIO', v),
            },
            {
              title: 'Participación en investigación',
              description:
                'Autoriza el uso de métricas seudonimizadas del piloto. Nunca incluye tu nombre ni conversaciones completas.',
              value: research,
              icon: Database,
              action: (v: boolean) => consent('RESEARCH', v),
            },
          ].map(({ title, description, value, icon: Icon, action }) => (
            <article
              key={title}
              className="flex gap-4 rounded-3xl border bg-card p-6"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/8 text-primary">
                <Icon className="size-5" />
              </span>
              <div className="flex-1">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="max-w-xl">
                    <h3 className="font-bold">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {description}
                    </p>
                  </div>
                  <button
                    onClick={() => action(!value)}
                    type="button"
                    role="switch"
                    aria-checked={value}
                    aria-label={title}
                    className={`relative h-7 w-12 rounded-full transition ${value ? 'bg-primary' : 'bg-muted-foreground/30'}`}
                  >
                    <span
                      className={`absolute top-1 size-5 rounded-full bg-white transition ${value ? 'left-6' : 'left-1'}`}
                    />
                  </button>
                </div>
              </div>
            </article>
          ))}
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
            onClick={requestExport}
            className="flex w-full items-center gap-3 rounded-2xl border bg-card p-4 text-left text-sm font-bold"
          >
            <Download className="size-5 text-primary" /> Solicitar copia de mis
            datos
          </button>
        </aside>
      </div>
    </AppShell>
  );
}
