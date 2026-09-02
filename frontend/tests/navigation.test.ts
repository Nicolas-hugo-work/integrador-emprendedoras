import { describe, expect, it } from 'vitest';

import {
  firstAllowedHref,
  NAV_LINKS,
  visibleLinks,
} from '../app/lib/navigation';

const sin = () => false;
const con = (permisos: string[]) => (permission: string) =>
  permisos.includes(permission);

const EMPRENDEDORA = con([
  'business.manage_own',
  'finance.read_own',
  'finance.write_own',
  'conversation.manage_own',
]);

describe('navegación principal', () => {
  it('es la única fuente: incluye curaduría con su permiso', () => {
    const curaduria = NAV_LINKS.find((link) => link.href === '/curaduria');
    expect(curaduria?.permission).toBe('source.review');
  });

  it('oculta curaduría a quien no tiene el permiso', () => {
    const rutas = visibleLinks(EMPRENDEDORA).map((link) => link.href);
    expect(rutas).not.toContain('/curaduria');
    expect(rutas).toContain('/finanzas');
  });

  it('la muestra a quien sí lo tiene', () => {
    const rutas = visibleLinks(con(['source.review'])).map((link) => link.href);
    expect(rutas).toContain('/curaduria');
  });

  it('inicio y mi negocio exigen business.manage_own', () => {
    for (const href of ['/', '/emprendimiento']) {
      expect(NAV_LINKS.find((link) => link.href === href)?.permission).toBe(
        'business.manage_own',
      );
    }
  });

  it('la curadora no ve la aplicación de emprendedora', () => {
    const rutas = visibleLinks(con(['source.review', 'source.publish'])).map(
      (link) => link.href,
    );
    expect(rutas).not.toContain('/');
    expect(rutas).not.toContain('/finanzas');
    expect(rutas).not.toContain('/asistente');
    expect(rutas).toContain('/curaduria');
  });

  it('cada rol de staff aterriza en su pantalla principal', () => {
    const administradora = con(['account.suspend', 'audit.read']);
    const auditora = con(['audit.read']);
    expect(firstAllowedHref(administradora)).toBe('/administracion');
    expect(firstAllowedHref(auditora)).toBe('/auditoria');
    expect(visibleLinks(auditora).map((l) => l.href)).not.toContain(
      '/administracion',
    );
  });

  it('privacidad no exige permiso: es un derecho de toda cuenta', () => {
    const privacidad = NAV_LINKS.find((link) => link.href === '/privacidad');
    expect(privacidad?.permission).toBeUndefined();
    expect(visibleLinks(sin).map((link) => link.href)).toEqual(['/privacidad']);
  });
});

describe('primera pantalla tras ingresar', () => {
  it('la emprendedora aterriza en Inicio', () => {
    expect(firstAllowedHref(EMPRENDEDORA)).toBe('/');
  });

  it('la curadora aterriza en Curaduría, no en el panel de emprendedora', () => {
    expect(firstAllowedHref(con(['source.review']))).toBe('/curaduria');
  });

  it('un rol sin funciones aterriza en Privacidad y conserva sus derechos', () => {
    expect(firstAllowedHref(sin)).toBe('/privacidad');
  });
});

describe('un enlace que abren varios permisos', () => {
  it('evaluación la abren la curaduría y la auditoría', () => {
    const evaluacion = NAV_LINKS.find((link) => link.href === '/evaluacion');
    expect(evaluacion?.permission).toEqual(['source.review', 'audit.read']);
  });

  it('la ve quien tiene cualquiera de los dos', () => {
    for (const permiso of ['source.review', 'audit.read']) {
      const rutas = visibleLinks(con([permiso])).map((link) => link.href);
      expect(rutas).toContain('/evaluacion');
    }
  });

  it('no la ve la emprendedora', () => {
    const rutas = visibleLinks(EMPRENDEDORA).map((link) => link.href);
    expect(rutas).not.toContain('/evaluacion');
  });

  it('sin ningún permiso solo queda privacidad', () => {
    expect(visibleLinks(sin).map((link) => link.href)).toEqual(['/privacidad']);
  });
});

describe('dónde aterriza cada rol', () => {
  it('evaluación no le roba la primera pantalla a nadie', () => {
    expect(firstAllowedHref(con(['source.review']))).toBe('/curaduria');
    expect(firstAllowedHref(con(['audit.read']))).toBe('/auditoria');
    expect(firstAllowedHref(con(['account.suspend', 'audit.read']))).toBe(
      '/administracion',
    );
  });
});
