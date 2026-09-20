import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Kawsay - Autonomía económica',
    short_name: 'Kawsay',
    description: 'Herramientas sencillas para fortalecer tu negocio.',
    id: '/',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#fbf8f2',
    theme_color: '#642447',
    lang: 'es',
    icons: [
      {
        src: '/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'maskable',
      },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  };
}
