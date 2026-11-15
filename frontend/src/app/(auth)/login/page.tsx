"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { post } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import type { Me } from "@/lib/types";

export default function Login() {
  const router = useRouter();
  const { setMe, refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState<Me | null>(null);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const { busy, error, run } = useAction();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const me = await run(() => post<Me>("/auth/login", { email, password }));
    if (!me) return;
    setMe(me);
    if (me.mfa_required) {
      setPending(me);
      if (!me.mfa_enabled) {
        const s = await run(() => post<{ secret: string; otpauth_uri: string }>("/auth/mfa/setup"));
        if (s) setSetup(s);
      }
    } else router.replace(homeFor(me.role));
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    const me = await run(() => post<Me>("/auth/mfa/verify", { code }));
    if (!me) return;
    await refresh();
    router.replace(homeFor(me.role));
  }

  if (pending) {
    return (
      <form onSubmit={verify} className="grid gap-4">
        <h1 className="text-xl font-bold">Two-step verification</h1>
        {setup ? (
          <Alert>
            Staff accounts require an authenticator app (MFA). Add this key in your authenticator app, then enter the 6-digit code.
            <code className="mt-2 block break-all rounded bg-card p-2 text-xs text-foreground">{setup.secret}</code>
            <a className="mt-1 block text-xs underline" href={setup.otpauth_uri}>Open in authenticator app</a>
          </Alert>
        ) : <p className="text-sm text-muted-foreground">Enter the 6-digit code from your authenticator app.</p>}
        <Field label="6-digit code"><Input inputMode="numeric" autoComplete="one-time-code" maxLength={8} required value={code} onChange={(e) => setCode(e.target.value)} /></Field>
        {error && <Alert tone="error">{error}</Alert>}
        <Button type="submit" disabled={busy}>Verify</Button>
      </form>
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <h1 className="text-xl font-bold">Sign in</h1>
      <Field label="Email"><Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
      <Field label="Password"><Input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
      <div className="flex justify-between text-sm"><Link href="/forgot-password" className="text-accent hover:underline">Forgot password?</Link><Link href="/register" className="text-accent hover:underline">Create account</Link></div>
    </form>
  );
}
