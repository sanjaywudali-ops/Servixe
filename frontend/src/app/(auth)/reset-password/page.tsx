"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { post } from "@/lib/api";
import { useAction } from "@/lib/hooks";

function Form() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const { busy, error, run } = useAction();
  async function submit(e: React.FormEvent) { e.preventDefault(); if (await run(() => post("/auth/password/reset", { token, password }))) setDone(true); }
  if (done) return <Alert tone="success">Password updated. <Link href="/login" className="underline">Sign in</Link></Alert>;
  return (
    <form onSubmit={submit} className="grid gap-4">
      <h1 className="text-xl font-bold">Choose a new password</h1>
      <Field label="New password" hint="At least 10 characters, upper and lower case, and a number."><Input type="password" required minLength={10} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" disabled={busy || !token}>Update password</Button>
    </form>
  );
}
export default function Page() { return <Suspense><Form /></Suspense>; }
