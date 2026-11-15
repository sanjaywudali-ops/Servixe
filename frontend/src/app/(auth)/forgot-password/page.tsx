"use client";
import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { post } from "@/lib/api";
import { useAction } from "@/lib/hooks";

export default function Forgot() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { busy, error, run } = useAction();
  async function submit(e: React.FormEvent) { e.preventDefault(); if (await run(() => post("/auth/password/forgot", { email }))) setSent(true); }
  return sent ? <Alert tone="success">If an account exists for that email, we’ve sent a reset link. It is valid for one hour.</Alert> : (
    <form onSubmit={submit} className="grid gap-4">
      <h1 className="text-xl font-bold">Reset your password</h1>
      <Field label="Email"><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" disabled={busy}>Send reset link</Button>
      <Link href="/login" className="text-center text-sm text-accent hover:underline">Back to sign in</Link>
    </form>
  );
}
