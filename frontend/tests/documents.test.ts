import { describe, expect, it } from 'vitest';

import { normalizeSourceUrl, splitIntoFragments } from '../app/lib/documents';

const PARRAFO = (n: number) =>
  `Parrafo numero ${n} con suficiente texto como para superar el minimo que exige el backend.`;

describe('partir un documento en fragmentos', () => {
  it('separa por líneas en blanco', () => {
    const { fragments, duplicatesDropped } = splitIntoFragments(
      `${PARRAFO(1)}\n\n${PARRAFO(2)}\n\n${PARRAFO(3)}`,
    );
    expect(fragments).toHaveLength(3);
    expect(duplicatesDropped).toBe(0);
    expect(fragments[0].content).toBe(PARRAFO(1));
  });

  it('toma una línea corta sin punto como título del siguiente', () => {
    const { fragments } = splitIntoFragments(
      `Requisitos de registro\n\n${PARRAFO(1)}\n\n${PARRAFO(2)}`,
    );
    expect(fragments).toHaveLength(2);
    expect(fragments[0].heading).toBe('Requisitos de registro');
    expect(fragments[0].content).toBe(PARRAFO(1));
    expect(fragments[1].heading).toBeUndefined();
  });

  it('descarta duplicados exactos y dice cuántos', () => {
    const { fragments, duplicatesDropped } = splitIntoFragments(
      `${PARRAFO(1)}\n\n${PARRAFO(2)}\n\n${PARRAFO(1)}`,
    );
    expect(fragments).toHaveLength(2);
    expect(duplicatesDropped).toBe(1);
  });

  it('corta un párrafo muy largo por frases', () => {
    const larga = 'Esta es una frase de longitud media que se repite. '.repeat(
      60,
    );
    const { fragments } = splitIntoFragments(larga);
    expect(fragments.length).toBeGreaterThan(1);
    for (const fragment of fragments) {
      expect(fragment.content.length).toBeLessThanOrEqual(1400);
      expect(fragment.content.length).toBeGreaterThanOrEqual(20);
    }
  });

  it('nunca devuelve un fragmento por debajo del mínimo del backend', () => {
    const { fragments } = splitIntoFragments(`${PARRAFO(1)}\n\ncorto\n\nx`);
    for (const fragment of fragments) {
      expect(fragment.content.length).toBeGreaterThanOrEqual(20);
    }
  });

  it('un texto vacío no produce fragmentos', () => {
    expect(splitIntoFragments('').fragments).toEqual([]);
    expect(splitIntoFragments('   \n\n  ').fragments).toEqual([]);
  });

  it('colapsa los saltos de línea dentro de un mismo párrafo', () => {
    const { fragments } = splitIntoFragments(
      'Una linea del documento\nque venia cortada por el PDF y sigue aqui.',
    );
    expect(fragments).toHaveLength(1);
    expect(fragments[0].content).not.toContain('\n');
  });
});

describe('normalizar el enlace oficial', () => {
  it('antepone https cuando falta', () => {
    expect(normalizeSourceUrl('www.seprec.gob.bo')).toBe(
      'https://www.seprec.gob.bo',
    );
  });

  it('respeta el esquema existente', () => {
    expect(normalizeSourceUrl('https://impuestos.gob.bo/guia')).toBe(
      'https://impuestos.gob.bo/guia',
    );
    expect(normalizeSourceUrl('http://ine.gob.bo')).toBe('http://ine.gob.bo');
  });

  it('recorta espacios y no inventa nada sobre un valor vacío', () => {
    expect(normalizeSourceUrl('  www.x.bo  ')).toBe('https://www.x.bo');
    expect(normalizeSourceUrl('   ')).toBe('');
  });
});
