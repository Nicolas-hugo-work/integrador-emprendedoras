'use client';

import {
  BookOpenCheck,
  Bot,
  Goal,
  LayoutDashboard,
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

/** Filtrado puro, para poder probarlo sin montar componentes. */
export function visibleLinks(has: (permission: string) => boolean): NavLink[] {
  return NAV_LINKS.filter((link) => !link.permission || has(link.permission));
}

/** Enlaces que la usuaria actual puede usar, según sus permisos. */
export function useNavLinks(): NavLink[] {
  const { has } = useSession();
  return visibleLinks(has);
}
