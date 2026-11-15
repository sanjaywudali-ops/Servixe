"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import type { Me } from "@/lib/types";

export default function Register() {
  const router = useRouter();
  const { setMe } = useAuth();
  const [f, setF] = useState({ full_name: "", email: "", password: "", country: "", phone: "", whatsapp_opt_in: false });
  const { busy, error, run } = useAction();
  const set = (k: string, v: string | boolean) => setF((p) => ({ ...p, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const me = await run(() => post<Me>("/auth/register", { ...f, phone: f.phone || null }));
    if (me) { setMe(me); router.replace("/portal"); }
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <h1 className="text-xl font-bold">Create your account</h1>
      <Field label="Full name"><Input required minLength={2} autoComplete="name" value={f.full_name} onChange={(e) => set("full_name", e.target.value)} /></Field>
      <Field label="Email"><Input type="email" required autoComplete="email" value={f.email} onChange={(e) => set("email", e.target.value)} /></Field>
      <Field label="Country you live in"><Input required autoComplete="country-name" value={f.country} onChange={(e) => set("country", e.target.value)} /></Field>
      <Field label="Phone (optional, with country code)"><Input type="tel" autoComplete="tel" value={f.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
      <Field label="Password" hint="At least 10 characters, with upper and lower case letters and a number."><Input type="password" required minLength={10} autoComplete="new-password" value={f.password} onChange={(e) => set("password", e.target.value)} /></Field>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={f.whatsapp_opt_in} onChange={(e) => set("whatsapp_opt_in", e.target.checked)} /> Send me updates on WhatsApp (optional; you can change this later).</label>
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" variant="accent" disabled={busy}>{busy ? "Creating…" : "Create account"}</Button>
      <p className="text-center text-sm">Already registered? <Link href="/login" className="text-accent hover:underline">Sign in</Link></p>
    </form>
  );
}
