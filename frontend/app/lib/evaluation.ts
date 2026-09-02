/**
 * Comparar dos corridas del banco de evaluación.
 *
 * Una corrida sola dice poco: el número que importa es el que cambia entre dos
 * implementaciones de recuperación. Esta es la parte de la pantalla que se
 * puede verificar sin montar componentes, así que vive aquí.
 */

import type { EvaluationResult, EvaluationRunDetail } from '../types/api';

export type Rates = {
  passed: number;
  recall: number;
  cited: number;
  warned: number;
  abstained: number;
};

const EMPTY: Rates = {
  passed: 0,
  recall: 0,
  cited: 0,
  warned: 0,
  abstained: 0,
};

/** Proporciones de una corrida. Sin casos, todo vale cero y no `NaN`. */
export function runRates(results: EvaluationResult[]): Rates {
  if (results.length === 0) return EMPTY;
  const share = (count: number) => count / results.length;
  return {
    passed: share(results.filter((row) => row.passed).length),
    recall: share(
      results.reduce((total, row) => total + row.retrieval_recall, 0),
    ),
    cited: share(results.filter((row) => row.citation_present).length),
    warned: share(results.filter((row) => row.warning_complete).length),
    abstained: share(results.filter((row) => row.abstained).length),
  };
}

export type Change = 'mejora' | 'retroceso' | 'igual' | 'incomparable';

export type CaseComparison = {
  case_code: string;
  category: string;
  before: EvaluationResult | null;
  after: EvaluationResult | null;
  change: Change;
};

function classify(
  before: EvaluationResult | null,
  after: EvaluationResult | null,
): Change {
  // Un caso que solo existe en una de las dos corridas no se puede comparar:
  // el conjunto ganó o perdió casos entre una y otra.
  if (!before || !after) return 'incomparable';
  if (before.passed !== after.passed) return after.passed ? 'mejora' : 'retroceso';
  if (after.retrieval_recall > before.retrieval_recall) return 'mejora';
  if (after.retrieval_recall < before.retrieval_recall) return 'retroceso';
  return 'igual';
}

/**
 * Empareja los casos de dos corridas por su código.
 *
 * Por código y no por posición: dos corridas del mismo conjunto pueden traer
 * distinto número de casos si alguien añadió uno entre medio, y alinearlas por
 * índice compararía casos que no tienen nada que ver.
 *
 * El orden de salida es el de la corrida posterior, con los casos que solo
 * estaban en la anterior al final: lo que se está mirando es el después.
 */
export function compareRuns(
  before: EvaluationRunDetail,
  after: EvaluationRunDetail,
): CaseComparison[] {
  const anteriores = new Map(before.results.map((row) => [row.case_code, row]));
  const comparaciones: CaseComparison[] = after.results.map((row) => {
    const anterior = anteriores.get(row.case_code) ?? null;
    anteriores.delete(row.case_code);
    return {
      case_code: row.case_code,
      category: row.category,
      before: anterior,
      after: row,
      change: classify(anterior, row),
    };
  });

  for (const huerfano of anteriores.values()) {
    comparaciones.push({
      case_code: huerfano.case_code,
      category: huerfano.category,
      before: huerfano,
      after: null,
      change: 'incomparable',
    });
  }
  return comparaciones;
}

/** Resumen en una línea, para no obligar a leer la tabla entera. */
export function summarize(comparisons: CaseComparison[]): string {
  const cuenta = (change: Change) =>
    comparisons.filter((row) => row.change === change).length;
  const mejoras = cuenta('mejora');
  const retrocesos = cuenta('retroceso');

  if (mejoras === 0 && retrocesos === 0) {
    return 'Ningún caso cambió de resultado entre las dos corridas.';
  }
  const partes: string[] = [];
  if (mejoras) partes.push(`${mejoras} ${mejoras === 1 ? 'mejora' : 'mejoras'}`);
  if (retrocesos) {
    partes.push(
      `${retrocesos} ${retrocesos === 1 ? 'retroceso' : 'retrocesos'}`,
    );
  }
  return `${partes.join(' y ')} sobre ${comparisons.length} casos.`;
}

/** Porcentaje sin decimales, que es toda la precisión que estos números tienen. */
export function asPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
