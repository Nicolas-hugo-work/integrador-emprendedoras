/**
 * Preparación de un documento para la curaduría.
 *
 * Antes la curadora pegaba el documento entero en un campo y después volvía a
 * copiar trozo por trozo en otro formulario. Aquí el texto se parte solo, y la
 * pantalla muestra el resultado para que lo revise antes de guardar.
 *
 * Funciones puras a propósito: es la parte del cambio que se puede verificar,
 * porque el proyecto no tiene pruebas de componentes.
 */

/** Una línea corta y sin punto final se toma como título del fragmento. */
const HEADING_MAX = 80;

/** Mínimo que exige `SourceChunkItem.content` en el backend. */
const MIN_CONTENT = 20;

/** Tamaño al que se apunta al cortar un párrafo largo. */
const TARGET_LENGTH = 900;

/** A partir de aquí un párrafo se corta por frases. */
const MAX_LENGTH = 1400;

export type Fragment = { heading?: string; content: string };

export type SplitResult = {
  fragments: Fragment[];
  /**
   * Cuántos fragmentos idénticos se descartaron. `source_chunks` tiene
   * unicidad sobre `(versión, hash del contenido)`, así que enviarlos haría
   * fallar la carga entera; en un documento normativo repetir un párrafo es
   * frecuente.
   */
  duplicatesDropped: number;
};

function intoParagraphs(text: string): string[] {
  return text
    .replace(/\r\n?/gu, '\n')
    .split(/\n\s*\n/u)
    .map((paragraph) => paragraph.trim().replace(/\s*\n\s*/gu, ' '))
    .filter(Boolean);
}

function looksLikeHeading(text: string): boolean {
  return text.length <= HEADING_MAX && !/[.]$/u.test(text);
}

function intoSentences(text: string): string[] {
  return text.match(/[^.;:!?]+[.;:!?]*\s*/gu) ?? [text];
}

function splitLongParagraph(text: string): string[] {
  if (text.length <= MAX_LENGTH) return [text];

  const pieces: string[] = [];
  let current = '';
  for (const sentence of intoSentences(text)) {
    const candidate = (current + sentence).trim();
    if (current && candidate.length > TARGET_LENGTH) {
      pieces.push(current.trim());
      current = sentence;
    } else {
      current = current + sentence;
    }
  }
  if (current.trim()) pieces.push(current.trim());
  return pieces;
}

/** Une hacia atrás lo que no llega al mínimo que acepta el backend. */
function mergeTooShort(fragments: Fragment[]): Fragment[] {
  const merged: Fragment[] = [];
  for (const fragment of fragments) {
    const previous = merged[merged.length - 1];
    if (fragment.content.length < MIN_CONTENT && previous) {
      previous.content = `${previous.content} ${fragment.content}`.trim();
    } else {
      merged.push({ ...fragment });
    }
  }
  // Si el primero quedó corto y no había anterior, se une con el siguiente.
  if (merged.length > 1 && merged[0].content.length < MIN_CONTENT) {
    merged[1].content = `${merged[0].content} ${merged[1].content}`.trim();
    merged[1].heading = merged[0].heading ?? merged[1].heading;
    merged.shift();
  }
  return merged.filter((fragment) => fragment.content.length >= MIN_CONTENT);
}

export function splitIntoFragments(text: string): SplitResult {
  const paragraphs = intoParagraphs(text);
  const raw: Fragment[] = [];
  let pendingHeading: string | undefined;

  paragraphs.forEach((paragraph, index) => {
    const isLast = index === paragraphs.length - 1;
    if (!isLast && looksLikeHeading(paragraph)) {
      pendingHeading = paragraph;
      return;
    }
    splitLongParagraph(paragraph).forEach((piece, position) => {
      raw.push({
        // El título solo encabeza el primer trozo del párrafo que titulaba.
        heading: position === 0 ? pendingHeading : undefined,
        content: piece,
      });
    });
    pendingHeading = undefined;
  });

  const merged = mergeTooShort(raw);

  const seen = new Set<string>();
  const fragments: Fragment[] = [];
  let duplicatesDropped = 0;
  for (const fragment of merged) {
    if (seen.has(fragment.content)) {
      duplicatesDropped += 1;
      continue;
    }
    seen.add(fragment.content);
    fragments.push(fragment);
  }

  return { fragments, duplicatesDropped };
}

/**
 * Completa el enlace oficial cuando falta el esquema.
 *
 * El campo exigía `type="url"`, así que `www.seprec.gob.bo` se rechazaba sin
 * decir por qué.
 */
export function normalizeSourceUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (/^https?:\/\//iu.test(trimmed)) return trimmed;
  return `https://${trimmed.replace(/^\/+/u, '')}`;
}
