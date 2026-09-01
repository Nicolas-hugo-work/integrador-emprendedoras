import Link from 'next/link';
import { ArrowLeft, ShieldCheck, Sparkles } from 'lucide-react';

export function AuthFrame({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen bg-background lg:grid-cols-[0.9fr_1.1fr]">
      <section className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col">
        <span className="absolute -left-28 bottom-20 size-80 rounded-full border-[48px] border-white/5" />
        <Link href="/" className="relative flex items-center gap-3"><span className="grid size-11 place-items-center rounded-2xl bg-white/12"><Sparkles className="size-5" /></span><strong className="font-heading text-xl">Kawsay</strong></Link>
        <div className="relative my-auto max-w-lg"><p className="text-xs font-bold uppercase tracking-[0.16em] text-white/60">Tecnología con propósito</p><h2 className="mt-5 font-heading text-4xl font-bold leading-tight">Tu información financiera, tus decisiones y tus datos bajo tu control.</h2><p className="mt-5 leading-7 text-white/70">Una herramienta pensada para emprendedoras bolivianas, con lenguaje claro y fuentes oficiales.</p></div>
        <div className="relative flex items-center gap-2 text-sm text-white/65"><ShieldCheck className="size-4" /> Tus conversaciones privadas no se usan para entrenar modelos.</div>
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <Link href="/" className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-primary"><ArrowLeft className="size-4" /> Volver al inicio</Link>
          <div className="mb-8 lg:hidden"><span className="inline-flex items-center gap-2 font-heading text-xl font-bold text-primary"><Sparkles className="size-5" /> Kawsay</span></div>
          <h1 className="font-heading text-3xl font-bold tracking-tight">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </main>
  );
}
