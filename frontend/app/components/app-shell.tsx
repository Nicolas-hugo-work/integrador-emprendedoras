'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Bot,
  Goal,
  LayoutDashboard,
  LogOut,
  Menu,
  BookOpenCheck,
  ShieldCheck,
  Sparkles,
  WalletCards,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { clearTokens } from '../lib/api';
import { useSession } from '../lib/session';

const links = [
  { href: '/', label: 'Inicio', icon: LayoutDashboard },
  { href: '/emprendimiento', label: 'Mi negocio', icon: Goal },
  { href: '/finanzas', label: 'Finanzas', icon: WalletCards },
  { href: '/asistente', label: 'Asistente', icon: Bot },
  { href: '/privacidad', label: 'Privacidad', icon: ShieldCheck },
  {
    href: '/curaduria',
    label: 'Curaduría',
    icon: BookOpenCheck,
    permission: 'source.review',
  },
];

export function AppShell({
  title,
  eyebrow,
  children,
  action,
}: {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { has } = useSession();
  // Solo se muestra lo que la usuaria realmente puede hacer.
  const visible = links.filter(
    (link) => !link.permission || has(link.permission),
  );
  function logout() {
    clearTokens();
    router.push('/login');
  }
  return (
    <main className="min-h-screen bg-background">
      <aside
        className={`${open ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r bg-sidebar p-5 transition-transform lg:translate-x-0`}
      >
        <div className="mb-9 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-2xl bg-primary text-white">
              <Sparkles className="size-5" />
            </span>
            <span>
              <strong className="block font-heading text-lg">Kawsay</strong>
              <small className="text-muted-foreground">
                Impulsa tu autonomía
              </small>
            </span>
          </Link>
          <button
            onClick={() => setOpen(false)}
            className="lg:hidden"
            aria-label="Cerrar menú"
          >
            <X />
          </button>
        </div>
        <nav className="space-y-1">
          {visible.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${path === href ? 'bg-primary text-white' : 'hover:bg-sidebar-accent'}`}
            >
              <Icon className="size-5" />
              {label}
            </Link>
          ))}
        </nav>
        <button
          onClick={logout}
          className="mt-auto flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
        >
          <LogOut className="size-5" /> Cerrar sesión
        </button>
      </aside>
      {open && (
        <button
          className="fixed inset-0 z-30 bg-black/20 lg:hidden"
          onClick={() => setOpen(false)}
          aria-label="Cerrar navegación"
        />
      )}
      <section className="lg:pl-72">
        <header className="sticky top-0 z-20 flex min-h-20 items-center justify-between border-b bg-background/90 px-5 py-3 backdrop-blur sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOpen(true)}
              className="grid size-10 place-items-center rounded-xl border bg-card lg:hidden"
              aria-label="Abrir navegación"
            >
              <Menu className="size-5" />
            </button>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                {eyebrow}
              </p>
              <h1 className="font-heading text-xl font-bold sm:text-2xl">
                {title}
              </h1>
            </div>
          </div>
          {action}
        </header>
        <div className="mx-auto max-w-7xl p-5 sm:p-8 lg:p-10">{children}</div>
      </section>
    </main>
  );
}
