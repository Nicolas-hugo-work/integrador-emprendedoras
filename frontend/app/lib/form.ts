/**
 * `FormData.get` devuelve `string | File | null`, así que convertirlo con
 * `String(...)` puede producir `[object Object]` en silencio. Estos ayudantes
 * obligan a tratar el caso no textual.
 */

export function fieldValue(data: FormData, name: string): string {
  const value = data.get(name);
  return typeof value === 'string' ? value : '';
}

export function optionalFieldValue(
  data: FormData,
  name: string,
): string | null {
  return fieldValue(data, name).trim() || null;
}
