'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowUpRight, BookOpenCheck, Bot, ChevronRight, CircleDollarSign, Goal,
  LayoutDashboard, Menu, MessageCircleQuestion, Plus, ShieldCheck, Sparkles,
  TrendingUp, UserRound, WalletCards,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { api, clearTokens, hasSession } from './lib/api';

const navItems = [
  { label: 'Inicio', icon: LayoutDashboard, active: true },
  { label: 'Mi negocio', icon: Goal, href: '/emprendimiento' },
  { label: 'Finanzas', icon: WalletCards, href: '/finanzas' },
  { label: 'Asistente', icon: Bot, href: '/asistente' },
  { label: 'Privacidad', icon: ShieldCheck, href: '/privacidad' },
];

type Business = { id: string; name: string };
type Summary = { income: string; outflow: string; balance: string };
type Movement = { id: string; movement_type: string; amount: string; occurred_on: string; note?: string };

export default function Home() {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [businessName, setBusinessName] = useState('tu negocio');
  const [summary, setSummary] = useState<Summary>({ income: '0', outflow: '0', balance: '0' });
  const [movements, setMovements] = useState<Movement[]>([]);

  useEffect(() => {
    if (!hasSession()) { router.replace('/login'); return; }
    api<Business[]>('/businesses').then(async (businesses) => {
      if (!businesses[0]) return;
      setBusinessName(businesses[0].name);
      const [totals, recent] = await Promise.all([
        api<Summary>(`/finance/summary?business_id=${businesses[0].id}`),
        api<Movement[]>(`/finance/movements?business_id=${businesses[0].id}`),
      ]);
      setSummary(totals);
      setMovements(recent.slice(0, 3));
    }).catch(() => undefined);
  }, [router]);

  function logout() { clearTokens(); router.push('/login'); }
  const money = (value: string) => `Bs ${Number(value).toLocaleString('es-BO', { minimumFractionDigits: 2 })}`;

  return (
    <main className="min-h-screen bg-background text-foreground">
      <aside className={`${mobileOpen ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-sidebar-border bg-sidebar px-5 py-6 transition-transform lg:translate-x-0`}>
        <Link href="/" className="mb-10 flex items-center gap-3 px-2" aria-label="Kawsay, página principal">
          <span className="grid size-11 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-sm"><Sparkles className="size-5" /></span>
          <span><strong className="block font-heading text-xl tracking-tight">Kawsay</strong><span className="text-xs text-muted-foreground">Impulsa tu autonomía</span></span>
        </Link>
        <nav className="space-y-1" aria-label="Navegación principal">
          {navItems.map(({ label, icon: Icon, active, href }) => (
            <Link key={label} href={href ?? '/'} onClick={() => setMobileOpen(false)} className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors ${active ? 'bg-primary text-primary-foreground shadow-sm' : 'text-sidebar-foreground hover:bg-sidebar-accent'}`}>
              <Icon className="size-5" />{label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto rounded-2xl border border-primary/15 bg-primary/5 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary"><BookOpenCheck className="size-4" /> Fuentes verificadas</div>
          <p className="text-xs leading-5 text-muted-foreground">Las orientaciones normativas muestran siempre su institución y fecha.</p>
        </div>
      </aside>

      {mobileOpen && <button className="fixed inset-0 z-30 bg-foreground/20 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Cerrar menú" />}

      <section className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b bg-background/90 px-5 backdrop-blur-md sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <button className="grid size-10 place-items-center rounded-xl border bg-card lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menú"><Menu className="size-5" /></button>
            <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Panel personal</p><h1 className="font-heading text-xl font-bold tracking-tight sm:text-2xl">Buenos días, emprendedora</h1></div>
          </div>
          <div className="flex items-center gap-3"><button onClick={logout} className="hidden text-sm font-semibold text-primary sm:block">Cerrar sesión</button><span className="grid size-10 place-items-center rounded-full bg-secondary text-secondary-foreground"><UserRound className="size-5" /></span></div>
        </header>

        <div className="mx-auto max-w-7xl space-y-7 p-5 sm:p-8 lg:p-10">
          <section className="overflow-hidden rounded-3xl bg-primary px-6 py-7 text-primary-foreground shadow-[0_20px_60px_-32px_var(--primary)] sm:px-8 sm:py-9">
            <div className="grid gap-7 md:grid-cols-[1fr_auto] md:items-end">
              <div><span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1.5 text-xs font-semibold"><Sparkles className="size-3.5" /> {businessName}</span><h2 className="max-w-2xl font-heading text-2xl font-bold leading-tight sm:text-3xl">Tu saldo registrado es {money(summary.balance)}</h2><p className="mt-3 max-w-xl text-sm leading-6 text-primary-foreground/75">Registra los movimientos de hoy para mantener tu resumen al día.</p></div>
              <Link href="/finanzas" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-bold text-primary transition hover:-translate-y-0.5">Ver mis finanzas <ArrowUpRight className="size-4" /></Link>
            </div>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: 'Ingresos registrados', value: money(summary.income), note: 'Movimientos del negocio', icon: TrendingUp, tone: 'text-emerald-700 bg-emerald-50' },
              { label: 'Gastos y costos', value: money(summary.outflow), note: `${movements.length} movimientos recientes`, icon: WalletCards, tone: 'text-orange-700 bg-orange-50' },
              { label: 'Saldo estimado', value: money(summary.balance), note: 'Ingresos menos salidas', icon: CircleDollarSign, tone: 'text-primary bg-primary/8' },
              { label: 'Próximo paso', value: movements.length ? 'Al día' : 'Comenzar', note: 'Mantén tus registros', icon: Goal, tone: 'text-sky-700 bg-sky-50' },
            ].map(({ label, value, note, icon: Icon, tone }) => (
              <article key={label} className="rounded-2xl border bg-card p-5 shadow-sm"><div className={`mb-5 grid size-10 place-items-center rounded-xl ${tone}`}><Icon className="size-5" /></div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 font-heading text-2xl font-bold tracking-tight">{value}</p><p className="mt-2 text-xs font-medium text-muted-foreground">{note}</p></article>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
            <article className="rounded-3xl border bg-card p-5 shadow-sm sm:p-6">
              <div className="mb-6 flex items-center justify-between"><div><h2 className="font-heading text-lg font-bold">Movimientos recientes</h2><p className="mt-1 text-sm text-muted-foreground">Tu actividad más reciente</p></div><Link href="/finanzas" className="text-sm font-bold text-primary">Ver todos</Link></div>
              <div className="divide-y">{movements.length ? movements.map((movement) => {
                const positive = movement.movement_type === 'INCOME';
                return <div key={movement.id} className="flex items-center gap-4 py-4 first:pt-0 last:pb-0"><span className={`grid size-10 place-items-center rounded-full ${positive ? 'bg-emerald-50 text-emerald-700' : 'bg-orange-50 text-orange-700'}`}>{positive ? <TrendingUp className="size-4" /> : <WalletCards className="size-4" />}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{movement.note || (positive ? 'Ingreso' : 'Gasto o costo')}</p><p className="text-xs text-muted-foreground">{movement.occurred_on}</p></div><span className={`text-sm font-bold ${positive ? 'text-emerald-700' : 'text-foreground'}`}>{positive ? '+' : '-'} {money(movement.amount)}</span></div>;
              }) : <p className="py-6 text-center text-sm text-muted-foreground">Aún no registraste movimientos.</p>}</div>
              <Link href="/finanzas" className="mt-6 flex h-11 items-center justify-center gap-2 rounded-xl border border-dashed text-sm font-semibold text-primary hover:bg-primary/5"><Plus className="size-4" /> Registrar movimiento</Link>
            </article>

            <article className="relative overflow-hidden rounded-3xl bg-[#123d38] p-6 text-white shadow-sm"><span className="absolute -right-12 -top-12 size-40 rounded-full bg-white/5" /><div className="relative"><span className="mb-5 grid size-12 place-items-center rounded-2xl bg-white/12"><Bot className="size-6" /></span><p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">Asistente Kawsay</p><h2 className="mt-2 font-heading text-2xl font-bold leading-tight">¿Qué necesitas resolver hoy?</h2><p className="mt-3 text-sm leading-6 text-white/70">Pregunta sobre precios, finanzas o formalización. Te responderemos con fuentes cuando corresponda.</p><Link href="/asistente" className="mt-7 flex h-12 items-center justify-between rounded-xl bg-white px-4 text-sm font-bold text-[#123d38]">Hacer una pregunta <ChevronRight className="size-5" /></Link></div></article>
          </section>

          <section className="rounded-3xl border bg-card p-5 shadow-sm sm:p-6"><div className="grid gap-5 md:grid-cols-[auto_1fr_auto] md:items-center"><span className="grid size-12 place-items-center rounded-2xl bg-secondary text-secondary-foreground"><MessageCircleQuestion className="size-6" /></span><div><h2 className="font-heading text-lg font-bold">Completa el diagnóstico de tu negocio</h2><p className="mt-1 text-sm leading-6 text-muted-foreground">Con tus respuestas podremos darte orientaciones más útiles y un plan de próximos pasos.</p></div><button className="h-11 rounded-xl border px-5 text-sm font-bold text-primary hover:bg-primary/5">Continuar diagnóstico</button></div></section>
        </div>
      </section>
    </main>
  );
}
