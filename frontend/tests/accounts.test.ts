import { describe, expect, it } from 'vitest';

import { accountActions } from '../app/lib/accounts';

describe('acciones disponibles sobre una cuenta', () => {
  it('una cuenta activa se puede suspender', () => {
    expect(accountActions('ACTIVE')).toEqual({
      canSuspend: true,
      canReactivate: false,
    });
  });

  it('una cuenta pendiente de verificar también', () => {
    expect(accountActions('PENDING').canSuspend).toBe(true);
  });

  it('una suspendida solo se reactiva', () => {
    expect(accountActions('SUSPENDED')).toEqual({
      canSuspend: false,
      canReactivate: true,
    });
  });

  it('una eliminada no admite ninguna acción, y lo explica', () => {
    const acciones = accountActions('DELETED');
    expect(acciones.canSuspend).toBe(false);
    expect(acciones.canReactivate).toBe(false);
    expect(acciones.reason).toContain('purga');
  });

  it('un estado desconocido no habilita nada', () => {
    const acciones = accountActions('LO_QUE_SEA');
    expect(acciones.canSuspend).toBe(false);
    expect(acciones.canReactivate).toBe(false);
    expect(acciones.reason).toBeTruthy();
  });
});
