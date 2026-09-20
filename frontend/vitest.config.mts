import { defineConfig } from 'vitest/config';

/**
 * Vitest usa este archivo. El andamiaje de Vite + Cloudflare de otro
 * generador ya no forma parte del árbol.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
