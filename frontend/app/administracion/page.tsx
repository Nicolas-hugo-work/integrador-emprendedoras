'use client';

import { SubmitEvent, useCallback, useEffect, useState } from 'react';
import {
  CircleCheck,
  Eye,
  LoaderCircle,
  Search,
  ShieldAlert,
  ShieldBan,
  ShieldCheck,
} from 'lucide-react';

import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';
import { fieldValue } from '../lib/form';
import { useSession } from '../lib/session';
import type { Account, AlertStatus, SecurityAlert } from '../types/api';

const PAGE_SIZE = 50;

const SEVERITY_STYLE: Record<string, string> = {
  LOW: 'bg-muted text-muted-foreground',
  MEDIUM: 'bg-amber-50 text-amber-800',
  HIGH: 'bg-orange-50 text-orange-800',
  CRITICAL: 'bg-red-50 text-red-700',
};

const STATUS_STYLE: Record<string, string> = {
  OPEN: 'bg-red-50 text-red-700',
  ACKNOWLEDGED: 'bg-amber-50 text-amber-800',
  RESOLVED: 'bg-emerald-50 text-emerald-700',
};

const ACCOUNT_STYLE: Record<string, string> = {
  ACTIVE: 'bg-emerald-50 text-emerald-700',
  SUSPENDED: 'bg-red-50 text-red-700',
  PENDING: 'bg-amber-50 text-amber-800',
  DELETED: 'bg-muted text-muted-foreground',
};

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function AdministrationPage() {
  const { has, loading: loadingSession } = useSession();
  const canAdminister = has('account.suspend');

  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [status, setStatus] = useState<AlertStatus | ''>('OPEN');
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async (current: AlertStatus | '') => {
    const query = new URLSearchParams({ limit: String(PAGE_SIZE) });
    if (current) query.set('status', current);
    return api<SecurityAlert[]>(`/security-alerts?${query.toString()}`);
  }, []);

  useEffect(() => {
    if (!canAdminister) return;
    let alive = true;
    void (async () => {
      try {
        const listed = await load(status);
        if (alive) setAlerts(listed);
      } catch (reason) {
        if (alive) setError(describe(reason, 'No se pudo cargar la cola.'));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [canAdminister, status, load]);

  async function run(action: () => Promise<void>, message: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(message);
    } catch (reason) {
      setError(describe(reason, 'No se pudo completar.'));
    } finally {
      setBusy(false);
    }
  }

  async function changeAlert(
    alert: SecurityAlert,
    accion: 'acknowledge' | 'resolve',
  ) {
    await run(
      async () => {
        await api(`/security-alerts/${alert.id}/${accion}`, { method: 'POST' });
        setAlerts(await load(status));
      },
      accion === 'resolve' ? 'Alerta cerrada.' : 'Alerta tomada.',
    );
  }

  async function openAccount(userId: string) {
    await run(async () => {
      setAccount(await api<Account>(`/accounts/${userId}`));
    }, 'Cuenta cargada desde la alerta.');
  }

  async function lookup(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const contacto = fieldValue(
      new FormData(event.currentTarget),
      'contact',
    ).trim();
    if (!contacto) return;
    await run(async () => {
      setAccount(
        await api<Account>(
          `/accounts/lookup?contact=${encodeURIComponent(contacto)}`,
        ),
      );
    }, 'Cuenta encontrada.');
  }

  async function suspend(target: Account) {
    const motivo = prompt('Motivo de la suspensión (queda en la auditoría):');
    if (!motivo || motivo.trim().length < 5) return;
    await run(async () => {
      setAccount(
        await api<Account>(`/accounts/${target.id}/suspend`, {
          method: 'POST',
          body: JSON.stringify({ reason: motivo.trim() }),
        }),
      );
    }, 'Cuenta suspendida: su acceso quedó cortado de inmediato.');
  }

  async function reactivate(target: Account) {
    await run(async () => {
      setAccount(
        await api<Account>(`/accounts/${target.id}/reactivate`, {
          method: 'POST',
        }),
      );
    }, 'Cuenta reactivada.');
  }

  if (loadingSession) {
    return (
      <AppShell eyebrow="Cola de trabajo" title="Administración">
        <div className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
        </div>
      </AppShell>
    );
  }

  if (!canAdminister) {
    return (
      <AppShell eyebrow="Cola de trabajo" title="Administración">
        <div className="mx-auto max-w-lg rounded-3xl border bg-card p-8 text-center">
          <ShieldAlert className="mx-auto size-10 text-amber-600" />
          <h2 className="mt-4 font-heading text-xl font-bold">
            No tienes acceso a la administración
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Esta sección requiere el permiso <code>account.suspend</code>.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell eyebrow="Cola de trabajo" title="Administración">
      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <section className="space-y-4">
          <div className="rounded-3xl border bg-card p-6">
            <div className="flex items-start gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-red-50 text-red-700">
                <ShieldAlert className="size-5" />
              </span>
              <div className="flex-1">
                <h2 className="font-heading text-lg font-bold">
                  Alertas de seguridad
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  El sistema abre una alerta cuando bloquea una cuenta o una
                  dirección por intentos fallidos. No registra el contacto
                  probado.
                </p>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {(['OPEN', 'ACKNOWLEDGED', 'RESOLVED', ''] as const).map(
                (value) => (
                  <button
                    key={value || 'TODAS'}
                    type="button"
                    onClick={() => setStatus(value)}
                    className={`rounded-xl border px-3 py-2 text-xs font-bold ${status === value ? 'border-primary bg-primary/5 text-primary' : ''}`}
                  >
                    {value || 'Todas'}
                  </button>
                ),
              )}
            </div>
          </div>

          <div className="rounded-3xl border bg-card p-6">
            {loading ? (
              <div className="grid min-h-40 place-items-center">
                <LoaderCircle className="animate-spin text-primary" />
              </div>
            ) : alerts.length ? (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <article key={alert.id} className="rounded-2xl border p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <strong className="text-sm">
                            {alert.alert_type}
                          </strong>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-bold ${SEVERITY_STYLE[alert.severity] ?? 'bg-muted'}`}
                          >
                            {alert.severity}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_STYLE[alert.status] ?? 'bg-muted'}`}
                          >
                            {alert.status}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {alert.description}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {new Date(alert.created_at).toLocaleString('es-BO')}
                          {alert.user_id ? '' : ' · sin cuenta asociada'}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2">
                        {alert.user_id && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => openAccount(alert.user_id as string)}
                            className="flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-bold disabled:opacity-50"
                          >
                            <Eye className="size-3.5" /> Ver cuenta
                          </button>
                        )}
                        {alert.status === 'OPEN' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => changeAlert(alert, 'acknowledge')}
                            className="h-9 rounded-lg border px-3 text-xs font-bold disabled:opacity-50"
                          >
                            Tomar
                          </button>
                        )}
                        {alert.status !== 'RESOLVED' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => changeAlert(alert, 'resolve')}
                            className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-white disabled:opacity-50"
                          >
                            <CircleCheck className="size-3.5" /> Cerrar
                          </button>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No hay alertas con ese estado.
              </p>
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <form
            onSubmit={lookup}
            className="grid gap-4 rounded-3xl border bg-card p-6"
          >
            <h2 className="font-heading text-lg font-bold">
              Buscar una cuenta
            </h2>
            <p className="text-xs leading-5 text-muted-foreground">
              Exige el correo o teléfono <strong>completo</strong>: no admite
              búsquedas parciales ni devuelve listados. Cada búsqueda queda
              auditada.
            </p>
            <label className="text-sm font-semibold">
              Contacto
              <input
                required
                name="contact"
                placeholder="nombre@correo.com"
                className="field"
              />
            </label>
            <button
              disabled={busy}
              className="flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50"
            >
              <Search className="size-4" /> Buscar
            </button>
          </form>

          {account && (
            <div className="rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">Cuenta</h2>
              <p className="mt-2 font-mono text-xs break-all text-muted-foreground">
                {account.id}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-bold ${ACCOUNT_STYLE[account.status] ?? 'bg-muted'}`}
                >
                  {account.status}
                </span>
                {account.roles.map((rol) => (
                  <span
                    key={rol}
                    className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold"
                  >
                    {rol}
                  </span>
                ))}
              </div>
              <div className="mt-5 grid gap-2">
                <button
                  type="button"
                  disabled={busy || account.status === 'SUSPENDED'}
                  onClick={() => suspend(account)}
                  className="flex h-11 items-center justify-center gap-2 rounded-xl border border-red-200 text-sm font-bold text-red-700 hover:bg-red-50 disabled:opacity-40"
                >
                  <ShieldBan className="size-4" /> Suspender
                </button>
                <button
                  type="button"
                  disabled={busy || account.status !== 'SUSPENDED'}
                  onClick={() => reactivate(account)}
                  className="flex h-11 items-center justify-center gap-2 rounded-xl border text-sm font-bold disabled:opacity-40"
                >
                  <ShieldCheck className="size-4" /> Reactivar
                </button>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Suspender corta el acceso de inmediato y revoca todas las
                sesiones. No se puede suspender a otra cuenta de administración
                ni a la propia.
              </p>
            </div>
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
