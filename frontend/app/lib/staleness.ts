/**
 * Texto de antigüedad para datos que no se acaban de comprobar.
 *
 * Función pura a propósito: es la parte que Vitest puede verificar sin
 * IndexedDB ni red.
 */
export function describeStaleness(
  fetchedAt: Date | null,
  now: Date = new Date(),
): string {
  if (!fetchedAt) return 'datos guardados';
  const elapsed = Math.max(0, now.getTime() - fetchedAt.getTime());
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return 'actualizado hace un momento';
  if (minutes === 1) return 'actualizado hace 1 minuto';
  if (minutes < 60) return `actualizado hace ${minutes} minutos`;
  const hours = Math.floor(minutes / 60);
  if (hours === 1) return 'actualizado hace 1 hora';
  if (hours < 24) return `actualizado hace ${hours} horas`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'actualizado hace 1 día';
  return `actualizado hace ${days} días`;
}
