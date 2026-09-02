/**
 * Qué se puede hacer con una cuenta según su estado.
 *
 * La regla vivía enredada en el JSX como
 * `disabled={busy || account.status === 'SUSPENDED'}`, y por eso una cuenta
 * `DELETED` mostraba «Suspender» habilitado: solo se descubría al recibir un
 * `409`. Extraída aquí, se puede probar y explicar.
 */

export type AccountActions = {
  canSuspend: boolean;
  canReactivate: boolean;
  /** Por qué no se puede hacer nada, para mostrarlo en vez de un botón mudo. */
  reason?: string;
};

export function accountActions(status: string): AccountActions {
  switch (status) {
    case 'ACTIVE':
    case 'PENDING':
      return { canSuspend: true, canReactivate: false };
    case 'SUSPENDED':
      return { canSuspend: false, canReactivate: true };
    case 'DELETED':
      return {
        canSuspend: false,
        canReactivate: false,
        reason:
          'La cuenta pidió su eliminación y su purga ya está programada: no se suspende ni se reactiva.',
      };
    default:
      return {
        canSuspend: false,
        canReactivate: false,
        reason: `Estado desconocido (${status}); no se ofrece ninguna acción.`,
      };
  }
}
