'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { SubmitEvent, useState } from 'react';
import { CheckCircle2, LoaderCircle } from 'lucide-react';
import { AuthFrame } from '../components/auth-frame';
import { api, saveTokens, TokenPair } from '../lib/api';
import { fieldValue } from '../lib/form';

import type { Registration } from '../types/api';

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = fieldValue(data, 'password');
    if (password !== fieldValue(data, 'confirm')) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const value = fieldValue(data, 'contact');
      const registration = await api<Registration>(
        '/auth/register',
        {
          method: 'POST',
          body: JSON.stringify({
            contact_type: value.includes('@') ? 'EMAIL' : 'PHONE',
            value,
            password,
            accept_account_terms: true,
          }),
        },
        false,
      );
      if (registration.verification_token)
        await api(
          '/auth/verify-contact',
          {
            method: 'POST',
            body: JSON.stringify({ token: registration.verification_token }),
          },
          false,
        );
      const tokens = await api<TokenPair>(
        '/auth/login',
        { method: 'POST', body: JSON.stringify({ contact: value, password }) },
        false,
      );
      saveTokens(tokens);
      router.push('/emprendimiento');
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'No fue posible crear la cuenta.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame
      title="Crea tu cuenta"
      description="Usa tu correo o teléfono. En el entorno local la verificación se completa automáticamente."
    >
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-semibold">
          Correo o teléfono
          <input
            name="contact"
            required
            className="mt-2 h-12 w-full rounded-xl border bg-card px-4 font-normal outline-none focus:ring-2 focus:ring-primary/25"
          />
        </label>
        <label className="block text-sm font-semibold">
          Contraseña
          <input
            name="password"
            required
            minLength={12}
            type="password"
            className="mt-2 h-12 w-full rounded-xl border bg-card px-4 font-normal outline-none focus:ring-2 focus:ring-primary/25"
          />
        </label>
        <label className="block text-sm font-semibold">
          Repite la contraseña
          <input
            name="confirm"
            required
            minLength={12}
            type="password"
            className="mt-2 h-12 w-full rounded-xl border bg-card px-4 font-normal outline-none focus:ring-2 focus:ring-primary/25"
          />
        </label>
        <label className="flex gap-3 rounded-xl border bg-card p-4 text-sm leading-5">
          <input required type="checkbox" className="mt-0.5 accent-primary" />
          <span>
            Acepto el aviso de privacidad y el tratamiento necesario para crear
            mi cuenta.
          </span>
        </label>
        <ul className="space-y-2 text-xs text-muted-foreground">
          <li className="flex gap-2">
            <CheckCircle2 className="size-4 text-emerald-600" /> Cifrado de
            contenido sensible
          </li>
          <li className="flex gap-2">
            <CheckCircle2 className="size-4 text-emerald-600" /> Puedes
            solicitar la eliminación de tus datos
          </li>
        </ul>
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
          {loading && <LoaderCircle className="size-4 animate-spin" />} Crear mi
          cuenta
        </button>
      </form>
      <p className="mt-7 text-center text-sm text-muted-foreground">
        ¿Ya tienes cuenta?{' '}
        <Link href="/login" className="font-bold text-primary">
          Ingresar
        </Link>
      </p>
    </AuthFrame>
  );
}
