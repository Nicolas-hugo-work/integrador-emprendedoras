import { defineConfig } from 'vitest/config';

/**
 * Vitest usa este archivo y no `vite.config.ts`, que quedó en el árbol como
 * andamiaje de otro generador y referencia paquetes que no están instalados.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
