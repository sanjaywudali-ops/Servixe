"use client";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { PageHeader } from "@/components/common";
import { del, patch, post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate } from "@/lib/utils";

interface Profile { full_name: string; country: string; phone: string | null; whatsapp_opt_in: boolean }
interface Sess { id: string; created_at: string; last_seen_at: string; ip: string | null; user_agent: string | null; current: boolean }

export default function Account() {
  const prof = useFetch<Profile>("/portal/profile");
  const sess = useFetch<Sess[]>("/auth/sessions");
  const [p, setP] = useState<Profile | null>(null);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const a = useAction();
  useEffect(() => { if (prof.data) setP(prof.data); }, [prof.data]);

  return (
    <>
      <PageHeader title="Account" />
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      {msg && <Alert tone="success" className="mb-4">{msg}</Alert>}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Profile & communication</CardTitle></CardHeader><CardContent>
          {p && <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await patch("/portal/profile", p); setMsg("Profile saved."); }); }}>
            <Field label="Full name"><Input value={p.full_name} onChange={(e) => setP({ ...p, full_name: e.target.value })} /></Field>
            <Field label="Country"><Input value={p.country} onChange={(e) => setP({ ...p, country: e.target.value })} /></Field>
            <Field label="Phone"><Input value={p.phone ?? ""} onChange={(e) => setP({ ...p, phone: e.target.value })} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={p.whatsapp_opt_in} onChange={(e) => setP({ ...p, whatsapp_opt_in: e.target.checked })} /> Receive updates on WhatsApp</label>
            <Button type="submit" disabled={a.busy}>Save</Button>
          </form>}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Change password</CardTitle></CardHeader><CardContent>
          <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await post("/auth/password/change", pw); setPw({ current_password: "", new_password: "" }); setMsg("Password changed. Other devices were signed out."); sess.reload(); }); }}>
            <Field label="Current password"><Input type="password" required autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
            <Field label="New password"><Input type="password" required minLength={10} autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
            <Button type="submit" disabled={a.busy}>Change password</Button>
          </form>
        </CardContent></Card>
        <Card className="lg:col-span-2"><CardHeader><CardTitle>Active sessions</CardTitle></CardHeader><CardContent><ul className="divide-y text-sm">
          {sess.data?.map((s) => <li key={s.id} className="flex items-center justify-between gap-3 py-2"><span className="min-w-0 truncate">{s.current ? "This device · " : ""}{s.user_agent?.slice(0, 60) || "Unknown device"} · {s.ip} · last seen {fmtDate(s.last_seen_at)}</span>{!s.current && <Button size="sm" variant="outline" onClick={() => a.run(async () => { await del(`/auth/sessions/${s.id}`); sess.reload(); })}>Sign out</Button>}</li>)}
        </ul></CardContent></Card>
      </div>
    </>
  );
}
