import { describe, expect, it } from 'vitest';

import {
  shouldReuseOnFailure,
  shouldStore,
} from '../app/lib/offline-cache';
import { describeStaleness } from '../app/lib/staleness';

describe('qué se cachea y qué no', () => {
  it('guarda solo un GET exitoso', () => {
    expect(shouldStore('GET', true)).toBe(true);
    expect(shouldStore(undefined, true)).toBe(true);
    expect(shouldStore('POST', true)).toBe(false);
    expect(shouldStore('PATCH', true)).toBe(false);
    expect(shouldStore('DELETE', true)).toBe(false);
    expect(shouldStore('GET', false)).toBe(false);
  });

  it('reutiliza la copia solo ante un fallo de red en GET', () => {
    expect(shouldReuseOnFailure('GET', true)).toBe(true);
    expect(shouldReuseOnFailure('GET', false)).toBe(false);
    expect(shouldReuseOnFailure('POST', true)).toBe(false);
  });
});

describe('describeStaleness', () => {
  const now = new Date('2026-09-20T18:00:00.000Z');

  it('habla de un momento si acaba de guardarse', () => {
    expect(describeStaleness(new Date('2026-09-20T17:59:30.000Z'), now)).toBe(
      'actualizado hace un momento',
    );
  });

  it('cuenta minutos, horas y días', () => {
    expect(describeStaleness(new Date('2026-09-20T17:57:00.000Z'), now)).toBe(
      'actualizado hace 3 minutos',
    );
    expect(describeStaleness(new Date('2026-09-20T15:00:00.000Z'), now)).toBe(
      'actualizado hace 3 horas',
    );
    expect(describeStaleness(new Date('2026-09-18T18:00:00.000Z'), now)).toBe(
      'actualizado hace 2 días',
    );
  });

  it('usa el singular cuando corresponde', () => {
    expect(describeStaleness(new Date('2026-09-20T17:00:00.000Z'), now)).toBe(
      'actualizado hace 1 hora',
    );
    expect(describeStaleness(new Date('2026-09-19T18:00:00.000Z'), now)).toBe(
      'actualizado hace 1 día',
    );
  });

  it('no inventa una fecha si no hay marca', () => {
    expect(describeStaleness(null, now)).toBe('datos guardados');
  });
});
