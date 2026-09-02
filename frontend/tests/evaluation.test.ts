import { describe, expect, it } from 'vitest';

import {
  asPercent,
  compareRuns,
  runRates,
  summarize,
} from '../app/lib/evaluation';
import type { EvaluationResult, EvaluationRunDetail } from '../app/types/api';

function resultado(
  case_code: string,
  overrides: Partial<EvaluationResult> = {},
): EvaluationResult {
  return {
    case_id: `id-${case_code}`,
    case_code,
    category: 'FORMALIZATION',
    passed: true,
    retrieval_recall: 1,
    citation_present: true,
    warning_complete: false,
    abstained: false,
    notes: null,
    ...overrides,
  };
}

function corrida(
  model_version: string,
  results: EvaluationResult[],
): EvaluationRunDetail {
  return {
    id: `corrida-${model_version}`,
    evaluation_set_id: 'conjunto',
    evaluation_set_name: 'Banco base',
    evaluation_set_version: '1',
    model_name: 'retrieval-only-mvp',
    model_version,
    status: 'COMPLETED',
    created_at: '2026-09-01T10:00:00',
    completed_at: '2026-09-01T10:00:05',
    total_cases: results.length,
    passed_cases: results.filter((row) => row.passed).length,
    results,
  };
}

describe('proporciones de una corrida', () => {
  it('cuenta cada medida sobre el total de casos', () => {
    const rates = runRates([
      resultado('A'),
      resultado('B', { passed: false, retrieval_recall: 0 }),
      resultado('C', {
        abstained: true,
        citation_present: false,
        retrieval_recall: 1,
      }),
      resultado('D', { warning_complete: true }),
    ]);
    expect(rates.passed).toBe(0.75);
    expect(rates.recall).toBe(0.75);
    expect(rates.cited).toBe(0.75);
    expect(rates.warned).toBe(0.25);
    expect(rates.abstained).toBe(0.25);
  });

  it('una corrida sin casos no produce NaN', () => {
    const rates = runRates([]);
    expect(Object.values(rates).every((value) => value === 0)).toBe(true);
    expect(asPercent(rates.passed)).toBe('0%');
  });
});

describe('comparar dos corridas', () => {
  it('marca mejora cuando un caso pasa de fallar a pasar', () => {
    const antes = corrida('v1', [
      resultado('FIN-01', { passed: false, retrieval_recall: 0 }),
    ]);
    const despues = corrida('v2', [resultado('FIN-01')]);

    const [fila] = compareRuns(antes, despues);
    expect(fila.change).toBe('mejora');
    expect(fila.before?.retrieval_recall).toBe(0);
    expect(fila.after?.retrieval_recall).toBe(1);
  });

  it('marca retroceso cuando deja de pasar', () => {
    const antes = corrida('v1', [resultado('FORM-01')]);
    const despues = corrida('v2', [resultado('FORM-01', { passed: false })]);
    expect(compareRuns(antes, despues)[0].change).toBe('retroceso');
  });

  it('un caso que pasa en las dos pero recupera más también es mejora', () => {
    const antes = corrida('v1', [resultado('MKT-01', { retrieval_recall: 0.5 })]);
    const despues = corrida('v2', [resultado('MKT-01', { retrieval_recall: 1 })]);
    expect(compareRuns(antes, despues)[0].change).toBe('mejora');
  });

  it('sin ningún cambio dice igual', () => {
    const antes = corrida('v1', [resultado('PII-01')]);
    const despues = corrida('v2', [resultado('PII-01')]);
    expect(compareRuns(antes, despues)[0].change).toBe('igual');
  });

  it('empareja por código y no por posición', () => {
    const antes = corrida('v1', [
      resultado('A', { passed: false }),
      resultado('B'),
    ]);
    // La corrida posterior trae los mismos casos en otro orden.
    const despues = corrida('v2', [resultado('B'), resultado('A')]);

    const porCodigo = new Map(
      compareRuns(antes, despues).map((row) => [row.case_code, row]),
    );
    expect(porCodigo.get('A')?.change).toBe('mejora');
    expect(porCodigo.get('B')?.change).toBe('igual');
  });

  it('un caso que solo está en una corrida queda como incomparable', () => {
    const antes = corrida('v1', [resultado('A'), resultado('VIEJO')]);
    const despues = corrida('v2', [resultado('A'), resultado('NUEVO')]);

    const comparaciones = compareRuns(antes, despues);
    expect(comparaciones).toHaveLength(3);
    const nuevo = comparaciones.find((row) => row.case_code === 'NUEVO');
    const viejo = comparaciones.find((row) => row.case_code === 'VIEJO');
    expect(nuevo?.change).toBe('incomparable');
    expect(nuevo?.before).toBeNull();
    expect(viejo?.change).toBe('incomparable');
    expect(viejo?.after).toBeNull();
  });
});

describe('resumen en una línea', () => {
  it('cuenta mejoras y retrocesos', () => {
    const antes = corrida('v1', [
      resultado('A', { passed: false }),
      resultado('B'),
      resultado('C'),
    ]);
    const despues = corrida('v2', [
      resultado('A'),
      resultado('B', { passed: false }),
      resultado('C'),
    ]);
    expect(summarize(compareRuns(antes, despues))).toBe(
      '1 mejora y 1 retroceso sobre 3 casos.',
    );
  });

  it('lo dice cuando nada cambió', () => {
    const antes = corrida('v1', [resultado('A')]);
    const despues = corrida('v2', [resultado('A')]);
    expect(summarize(compareRuns(antes, despues))).toContain(
      'Ningún caso cambió',
    );
  });
});
