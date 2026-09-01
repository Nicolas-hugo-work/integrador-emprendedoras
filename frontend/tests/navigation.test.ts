import { describe, expect, it } from 'vitest';

import { NAV_LINKS, visibleLinks } from '../app/lib/navigation';

const sin = () => false;
const con = (permisos: string[]) => (permission: string) =>
  permisos.includes(permission);

describe('navegación principal', () => {
  it('es la única fuente: incluye curaduría con su permiso', () => {
    const curaduria = NAV_LINKS.find((link) => link.href === '/curaduria');
    expect(curaduria?.permission).toBe('source.review');
  });

  it('oculta curaduría a quien no tiene el permiso', () => {
    const rutas = visibleLinks(sin).map((link) => link.href);
    expect(rutas).not.toContain('/curaduria');
    expect(rutas).toContain('/finanzas');
  });

  it('la muestra a quien sí lo tiene', () => {
    const rutas = visibleLinks(con(['source.review'])).map((link) => link.href);
    expect(rutas).toContain('/curaduria');
  });

  it('siempre deja visibles los enlaces sin permiso', () => {
    const libres = NAV_LINKS.filter((link) => !link.permission).map(
      (l) => l.href,
    );
    expect(visibleLinks(sin).map((link) => link.href)).toEqual(libres);
    expect(libres).toContain('/');
  });
});
