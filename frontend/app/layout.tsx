import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { PwaRegister } from './pwa-register';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'Kawsay | Autonomía económica', template: '%s | Kawsay' },
  description: 'Herramientas sencillas para fortalecer tu negocio y tu autonomía económica.',
  manifest: '/manifest.webmanifest',
};

export const viewport: Viewport = { themeColor: '#642447', width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body className={`${geistSans.variable} ${geistMono.variable} antialiased`}><PwaRegister />{children}</body></html>;
}
