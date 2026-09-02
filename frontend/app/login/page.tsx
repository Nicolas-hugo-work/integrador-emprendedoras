'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { SubmitEvent, useState } from 'react';
import { Eye, EyeOff, LoaderCircle } from 'lucide-react';
import { AuthFrame } from '../components/auth-frame';
import { api, saveTokens, TokenPair } from '../lib/api';
import { firstAllowedHref } from '../lib/navigation';
import type { User } from '../types/api';

export default function LoginPage() {
  const router = useRouter();
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    setError('');
    try {
      const tokens = await api<TokenPair>(
        '/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({
            contact: data.get('contact'),
            password: data.get('password'),
          }),
        },
        false,
      );
      saveTokens(tokens);
      const perfil = await api<User>('/me');
      router.push(
        firstAllowedHref((permiso) => perfil.permissions.includes(permiso)),
      );
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'No fue posible ingresar.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame
      title="Bienvenida de nuevo"
      description="Ingresa con el correo o teléfono que verificaste al crear tu cuenta."
    >
      <form className="space-y-5" onSubmit={submit}>
        <label className="block text-sm font-semibold">
          Correo o teléfono
          <input
            name="contact"
            required
            autoComplete="username"
            className="mt-2 h-12 w-full rounded-xl border bg-card px-4 font-normal outline-none focus:ring-2 focus:ring-primary/25"
            placeholder="nombre@correo.com"
          />
        </label>
        <label className="block text-sm font-semibold">
          Contraseña
          <span className="relative mt-2 block">
            <input
              name="password"
              required
              minLength={12}
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              className="h-12 w-full rounded-xl border bg-card px-4 pr-12 font-normal outline-none focus:ring-2 focus:ring-primary/25"
              placeholder="Mínimo 12 caracteres"
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {show ? (
                <EyeOff className="size-5" />
              ) : (
                <Eye className="size-5" />
              )}
            </button>
          </span>
        </label>
        {error && (
          <p
            role="alert"
            className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </p>
        )}
        <button
          disabled={loading}
          className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary font-bold text-primary-foreground disabled:opacity-60"
        >
          {loading && <LoaderCircle className="size-4 animate-spin" />} Ingresar
        </button>
      </form>
      <p className="mt-7 text-center text-sm text-muted-foreground">
        ¿Aún no tienes una cuenta?{' '}
        <Link href="/registro" className="font-bold text-primary">
          Crear cuenta
        </Link>
      </p>
    </AuthFrame>
  );
}
