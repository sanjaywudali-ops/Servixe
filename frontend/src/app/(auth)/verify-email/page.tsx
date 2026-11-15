"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Alert } from "@/components/ui/alert";
import { post } from "@/lib/api";

function Verify() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"working" | "ok" | "bad">("working");
  useEffect(() => { post("/auth/verify-email", { token }).then(() => setState("ok")).catch(() => setState("bad")); }, [token]);
  if (state === "working") return <p className="text-sm">Verifying…</p>;
  return state === "ok" ? <Alert tone="success">Email verified. <Link href="/login" className="underline">Continue</Link></Alert> : <Alert tone="error">This verification link is invalid or has expired.</Alert>;
}
export default function Page() { return <Suspense><Verify /></Suspense>; }
