'use client';

import Link from 'next/link';
import { SubmitEvent, useEffect, useMemo, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  LoaderCircle,
  Plus,
  WalletCards,
} from 'lucide-react';
import { AppShell } from '../components/app-shell';
import { api } from '../lib/api';

import type { Business, Category, Movement, Summary } from '../types/api';

export default function FinancePage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState('');
  const [categories, setCategories] = useState<Category[]>([]);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [summary, setSummary] = useState<Summary>({
    income: '0',
    outflow: '0',
    balance: '0',
  });
  const [type, setType] = useState('INCOME');
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const filteredCategories = useMemo(
    () => categories.filter((item) => item.movement_type === type),
    [categories, type],
  );
  useEffect(() => {
    Promise.all([
      api<Business[]>('/businesses'),
      api<Category[]>('/finance/categories'),
    ])
      .then(([items, cats]) => {
        setBusinesses(items);
        setCategories(cats);
        if (items[0]) setBusinessId(items[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!businessId) return;
    Promise.all([
      api<Movement[]>(`/finance/movements?business_id=${businessId}`),
      api<Summary>(`/finance/summary?business_id=${businessId}`),
    ])
      .then(([items, totals]) => {
        setMovements(items);
        setSummary(totals);
      })
      .catch((e) => setError(e.message));
  }, [businessId]);
  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setError('');
    try {
      const created = await api<Movement>('/finance/movements', {
        method: 'POST',
        body: JSON.stringify({
          business_id: businessId,
          category_id: data.get('category_id'),
          movement_type: type,
          scope: 'BUSINESS',
          amount: data.get('amount'),
          currency: 'BOB',
          occurred_on: data.get('occurred_on'),
          note: data.get('note') || null,
        }),
      });
      setMovements([created, ...movements]);
      const totals = await api<Summary>(
        `/finance/summary?business_id=${businessId}`,
      );
      setSummary(totals);
      setOpen(false);
      form.reset();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No se pudo registrar.',
      );
    }
  }
  const money = (value: string) =>
    `Bs ${Number(value).toLocaleString('es-BO', { minimumFractionDigits: 2 })}`;
  return (
    <AppShell
      eyebrow="Control sencillo"
      title="Mis finanzas"
      action={
        <button
          onClick={() => setOpen(!open)}
          className="hidden h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white sm:flex"
        >
          <Plus className="size-4" /> Nuevo movimiento
        </button>
      }
    >
      {loading ? (
        <div className="grid min-h-64 place-items-center">
          <LoaderCircle className="animate-spin text-primary" />
        </div>
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
                onChange={(e) => setBusinessId(e.target.value)}
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
              onClick={() => setOpen(!open)}
              className="flex h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white sm:hidden"
            >
              <Plus className="size-4" /> Registrar
            </button>
          </div>
          <section className="grid gap-4 sm:grid-cols-3">
            {[
              {
                label: 'Ingresos',
                value: summary.income,
                color: 'text-emerald-700',
                icon: ArrowUpRight,
              },
              {
                label: 'Gastos y costos',
                value: summary.outflow,
                color: 'text-orange-700',
                icon: ArrowDownRight,
              },
              {
                label: 'Saldo',
                value: summary.balance,
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
                <p className="mt-3 font-heading text-2xl font-bold">
                  {money(value)}
                </p>
              </article>
            ))}
          </section>
          {open && (
            <section className="rounded-3xl border bg-card p-6">
              <h2 className="font-heading text-lg font-bold">
                Registrar movimiento
              </h2>
              <form
                onSubmit={submit}
                className="mt-5 grid gap-4 sm:grid-cols-2"
              >
                <label className="text-sm font-semibold">
                  Tipo
                  <select
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="field"
                  >
                    <option value="INCOME">Ingreso</option>
                    <option value="EXPENSE">Gasto</option>
                    <option value="COST">Costo</option>
                  </select>
                </label>
                <label className="text-sm font-semibold">
                  Categoría
                  <select required name="category_id" className="field">
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
                    className="field"
                  />
                </label>
                <label className="text-sm font-semibold">
                  Fecha
                  <input
                    required
                    name="occurred_on"
                    type="date"
                    defaultValue={new Date().toISOString().slice(0, 10)}
                    className="field"
                  />
                </label>
                <label className="text-sm font-semibold sm:col-span-2">
                  Nota opcional
                  <input
                    name="note"
                    className="field"
                    placeholder="Descripción breve"
                  />
                </label>
                <button className="h-11 rounded-xl bg-primary px-5 text-sm font-bold text-white sm:col-span-2">
                  Guardar movimiento
                </button>
              </form>
            </section>
          )}
          {error && (
            <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {error}
            </p>
          )}
          <section className="rounded-3xl border bg-card p-6">
            <h2 className="font-heading text-lg font-bold">
              Historial de movimientos
            </h2>
            {movements.length ? (
              <div className="mt-4 divide-y">
                {movements.map((item) => (
                  <article
                    key={item.id}
                    className="flex items-center gap-4 py-4"
                  >
                    <span
                      className={`grid size-10 place-items-center rounded-full ${item.movement_type === 'INCOME' ? 'bg-emerald-50 text-emerald-700' : 'bg-orange-50 text-orange-700'}`}
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
