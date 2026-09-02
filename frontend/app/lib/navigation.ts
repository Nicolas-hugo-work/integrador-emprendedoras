'use client';

import {
  BookOpenCheck,
  Bot,
  Goal,
  LayoutDashboard,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';

import { useSession } from './session';

export type NavLink = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Código de permiso requerido. Sin él, el enlace es visible para todas. */
  permission?: string;
};

/**
 * Única fuente de la navegación principal.
 *
 * La lista estaba duplicada entre `AppShell` y la pantalla de inicio, así que
 * al añadir Curaduría en v0.3.0 el enlace aparecía en todas las pantallas menos
 * en la primera que se ve al ingresar. Ahora ambas leen de aquí.
 */
export const NAV_LINKS: NavLink[] = [
  {
    href: '/',
    label: 'Inicio',
    icon: LayoutDashboard,
    permission: 'business.manage_own',
  },
  {
    href: '/emprendimiento',
    label: 'Mi negocio',
    icon: Goal,
    permission: 'business.manage_own',
  },
  {
    href: '/finanzas',
    label: 'Finanzas',
    icon: WalletCards,
    permission: 'finance.read_own',
  },
  {
    href: '/asistente',
    label: 'Asistente',
    icon: Bot,
    permission: 'conversation.manage_own',
  },
  {
    href: '/curaduria',
    label: 'Curaduría',
    icon: BookOpenCheck,
    permission: 'source.review',
  },
  // Administración va antes que Auditoría: la cola de alertas es donde la
  // administradora trabaja, y la traza es solo lectura. Así cada rol aterriza
  // en su pantalla principal.
  {
    href: '/administracion',
    label: 'Administración',
    icon: ShieldAlert,
    permission: 'account.suspend',
  },
  {
    href: '/auditoria',
    label: 'Auditoría',
    icon: ScrollText,
    permission: 'audit.read',
  },
  // Privacidad va última y sin permiso a propósito: es un derecho de toda
  // cuenta, y así queda como refugio de un rol sin ninguna función.
  { href: '/privacidad', label: 'Privacidad', icon: ShieldCheck },
];

/** Filtrado puro, para poder probarlo sin montar componentes. */
export function visibleLinks(has: (permission: string) => boolean): NavLink[] {
  return NAV_LINKS.filter((link) => !link.permission || has(link.permission));
}

/**
 * Primera pantalla que la usuaria puede abrir.
 *
 * El login llevaba a `/` fijo, que es contenido enteramente de emprendedora:
 * una curadora aterrizaba en una pantalla que ahora le responderia 403.
 */
export function firstAllowedHref(has: (permission: string) => boolean): string {
  return visibleLinks(has)[0]?.href ?? '/privacidad';
}

/** Enlaces que la usuaria actual puede usar, según sus permisos. */
export function useNavLinks(): NavLink[] {
  const { has } = useSession();
  return visibleLinks(has);
}
