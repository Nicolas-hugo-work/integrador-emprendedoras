'use client';

import Link from 'next/link';
import { SubmitEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  LoaderCircle,
  Pencil,
  Plus,
  Trash2,
  WalletCards,
  X,
} from 'lucide-react';

import { useOffline } from 'next/offline';

import { AppShell } from '../components/app-shell';
import {
  api,
  apiCached,
  isNetworkError,
  OFFLINE_WRITE_ERROR,
} from '../lib/api';
import { fieldValue, optionalFieldValue } from '../lib/form';
import { describeStaleness } from '../lib/staleness';
import type { Business, Category, Movement, Summary } from '../types/api';

function describe(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function FinancePage() {
  const offline = useOffline();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState('');
  const [categories, setCategories] = useState<Category[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryFor, setSummaryFor] = useState('');
  const [stale, setStale] = useState(false);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [type, setType] = useState('INCOME');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Movement | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [bootFailed, setBootFailed] = useState(false);
  const [saving, setSaving] = useState(false);

  const filteredCategories = useMemo(
    () => categories.filter((item) => item.movement_type === type),
    [categories, type],
  );

  const reload = useCallback(async (id: string) => {
    const [items, totals] = await Promise.all([
      apiCached<Movement[]>(`/finance/movements?business_id=${id}`),
      apiCached<Summary>(`/finance/summary?business_id=${id}`),
    ]);
    setMovements(items.data);
    setSummary(totals.data);
    setSummaryFor(id);
    setStale(items.stale || totals.stale);
    setFetchedAt(totals.fetchedAt);
  }, []);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const [items, cats] = await Promise.all([
          apiCached<Business[]>('/businesses'),
          apiCached<Category[]>('/finance/categories'),
        ]);
        if (!alive) return;
        setBusinesses(items.data);
        setCategories(cats.data);
        if (items.stale || cats.stale) setStale(true);
        if (items.data[0]) setBusinessId(items.data[0].id);
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
        await reload(businessId);
      } catch (reason) {
        if (alive) setError(describe(reason, 'No se pudo cargar.'));
      }
    })();
    return () => {
      alive = false;
    };
  }, [businessId, reload]);

  function startEditing(movement: Movement) {
    setEditing(movement);
    setType(movement.movement_type);
    setOpen(true);
  }

  function cancelEditing() {
    setEditing(null);
    setOpen(false);
  }

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setError('');
    if (offline) {
      setError(OFFLINE_WRITE_ERROR);
      return;
    }
    const body = {
      category_id: fieldValue(data, 'category_id'),
      movement_type: type,
      amount: fieldValue(data, 'amount'),
      occurred_on: fieldValue(data, 'occurred_on'),
      note: optionalFieldValue(data, 'note'),
    };
    setSaving(true);
    try {
      if (editing) {
        await api<Movement>(`/finance/movements/${editing.id}`, {
          method: 'PATCH',
          body: JSON.stringify(body),
        });
      } else {
        await api<Movement>('/finance/movements', {
          method: 'POST',
          body: JSON.stringify({
            ...body,
            business_id: businessId,
            scope: 'BUSINESS',
            currency: 'BOB',
          }),
        });
      }
      await reload(businessId);
      cancelEditing();
      form.reset();
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

  async function remove(movement: Movement) {
    if (!confirm('Se quitará este movimiento de tu historial. ¿Continuar?'))
      return;
    setError('');
    if (offline) {
      setError(OFFLINE_WRITE_ERROR);
      return;
    }
    try {
      await api(`/finance/movements/${movement.id}`, { method: 'DELETE' });
      if (editing?.id === movement.id) cancelEditing();
      await reload(businessId);
    } catch (reason) {
      setError(
        isNetworkError(reason)
          ? OFFLINE_WRITE_ERROR
          : describe(reason, 'No se pudo eliminar.'),
      );
    }
  }

  const money = (value: string) =>
    `Bs ${Number(value).toLocaleString('es-BO', { minimumFractionDigits: 2 })}`;
  const visibleSummary = summaryFor === businessId ? summary : null;

  return (
    <AppShell
      eyebrow="Control sencillo"
      title="Mis finanzas"
      action={
        <button
          type="button"
          onClick={() => (open ? cancelEditing() : setOpen(true))}
          className="hidden h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white sm:flex"
        >
          <Plus className="size-4" /> Nuevo movimiento
        </button>
      }
    >
      {loading ? (
        <div
          aria-live="polite"
          className="grid min-h-64 place-items-center text-sm text-muted-foreground"
        >
          <LoaderCircle className="animate-spin text-primary" />
          <span className="sr-only">Cargando finanzas</span>
        </div>
      ) : bootFailed && !businesses.length ? (
        <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error || 'No se pudo cargar.'}
        </p>
      ) : !businesses.length ? (
        <div className="rounded-3xl border bg-card p-8 text-center">
          <WalletCards className="mx-auto size-10 text-primary" />
          <h2 className="mt-4 font-heading text-xl font-bold">
            Primero registra tu emprendimiento
          </h2>
          <Link
            href="/emprendimiento"
            className="mt-5 inline-flex h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white"
          >
            Ir a Mi negocio
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="text-sm font-semibold">
              Negocio{' '}
              <select
                value={businessId}
                onChange={(event) => setBusinessId(event.target.value)}
                className="ml-2 rounded-xl border bg-card px-3 py-2"
              >
                {businesses.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => (open ? cancelEditing() : setOpen(true))}
              className="flex h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white sm:hidden"
            >
              <Plus className="size-4" /> Registrar
            </button>
          </div>

          <section className="grid gap-4 sm:grid-cols-3">
            {[
              {
                label: 'Ingresos',
                value: visibleSummary ? money(visibleSummary.income) : '—',
                color: 'text-emerald-700',
                icon: ArrowUpRight,
              },
              {
                label: 'Gastos y costos',
                value: visibleSummary ? money(visibleSummary.outflow) : '—',
                color: 'text-orange-700',
                icon: ArrowDownRight,
              },
              {
                label: 'Saldo',
                value: visibleSummary ? money(visibleSummary.balance) : '—',
                color: 'text-primary',
                icon: WalletCards,
              },
            ].map(({ label, value, color, icon: Icon }) => (
              <article key={label} className="rounded-2xl border bg-card p-5">
                <div
                  className={`flex items-center gap-2 text-sm font-semibold ${color}`}
                >
                  <Icon className="size-4" /> {label}
                </div>
                <p
                  aria-live="polite"
                  className="mt-3 font-heading text-2xl font-bold"
                >
                  {value}
                </p>
              </article>
            ))}
          </section>
          {stale && (
            <p className="text-sm font-medium text-amber-800">
              {describeStaleness(fetchedAt)}
            </p>
          )}

          {open && (
            <section className="rounded-3xl border bg-card p-6">
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-lg font-bold">
                  {editing ? 'Corregir movimiento' : 'Registrar movimiento'}
                </h2>
                {editing && (
                  <button
                    type="button"
                    onClick={cancelEditing}
                    className="flex items-center gap-1 text-sm font-semibold text-muted-foreground"
                  >
                    <X className="size-4" /> Cancelar
                  </button>
                )}
              </div>
              <form
                key={editing?.id ?? 'nuevo'}
                onSubmit={submit}
                className="mt-5 grid gap-4 sm:grid-cols-2"
              >
                <label className="text-sm font-semibold">
                  Tipo
                  <select
                    value={type}
                    onChange={(event) => setType(event.target.value)}
                    className="field"
                  >
                    <option value="INCOME">Ingreso</option>
                    <option value="EXPENSE">Gasto</option>
                    <option value="COST">Costo</option>
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  Categoría
                  <select
                    required
                    name="category_id"
                    defaultValue={editing?.category_id ?? ''}
                    className="field"
                  >
                    <option value="">Selecciona</option>
                    {filteredCategories.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  Monto en Bs
                  <input
                    required
                    name="amount"
                    type="number"
                    min="0.01"
                    step="0.01"
                    defaultValue={editing?.amount ?? ''}
                    className="field"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Fecha
                  <input
                    required
                    name="occurred_on"
                    type="date"
                    defaultValue={
                      editing?.occurred_on ??
                      new Date().toISOString().slice(0, 10)
                    }
                    className="field"
                  />
                </label>
                <label className="text-sm font-semibold sm:col-span-2">
                  Nota opcional
                  <input
                    name="note"
                    defaultValue={editing?.note ?? ''}
                    className="field"
                    placeholder="Descripción breve"
                  />
                </label>
                <button
                  disabled={saving}
                  className="flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-60 sm:col-span-2"
                >
                  {saving && <LoaderCircle className="size-4 animate-spin" />}
                  {editing ? 'Guardar corrección' : 'Guardar movimiento'}
                </button>
              </form>
            </section>
          )}

          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {error}
            </p>
          )}

          <section className="rounded-3xl border bg-card p-6">
            <h2 className="font-heading text-lg font-bold">
              Historial de movimientos
            </h2>
            {!visibleSummary && error ? (
              <p className="mt-4 text-sm text-muted-foreground">
                No se pudieron cargar los movimientos.
              </p>
            ) : movements.length ? (
              <div className="mt-4 divide-y">
                {movements.map((item) => (
                  <article
                    key={item.id}
                    className="flex items-center gap-4 py-4"
                  >
                    <span
                      className={`grid size-10 shrink-0 place-items-center rounded-full ${item.movement_type === 'INCOME' ? 'bg-emerald-50 text-emerald-700' : 'bg-orange-50 text-orange-700'}`}
                    >
                      {item.movement_type === 'INCOME' ? (
                        <ArrowUpRight />
                      ) : (
                        <ArrowDownRight />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">
                        {item.note ||
                          (item.movement_type === 'INCOME'
                            ? 'Ingreso'
                            : 'Salida')}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.occurred_on}
                      </p>
                    </div>
                    <strong
                      className={
                        item.movement_type === 'INCOME'
                          ? 'text-emerald-700'
                          : ''
                      }
                    >
                      {item.movement_type === 'INCOME' ? '+' : '-'}{' '}
                      {money(item.amount)}
                    </strong>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        onClick={() => startEditing(item)}
                        aria-label={`Corregir movimiento del ${item.occurred_on}`}
                        className="grid size-9 place-items-center rounded-lg border text-muted-foreground hover:text-foreground"
                      >
                        <Pencil className="size-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(item)}
                        aria-label={`Eliminar movimiento del ${item.occurred_on}`}
                        className="grid size-9 place-items-center rounded-lg border border-red-200 text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">
                Aún no hay movimientos registrados.
              </p>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
