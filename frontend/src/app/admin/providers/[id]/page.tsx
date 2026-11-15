"use client";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { KV, PageHeader, State } from "@/components/common";
import { api, get, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate, label } from "@/lib/utils";

interface Doc { id: string; doc_type: string; filename: string; reference_last4: string | null; expires_at: string | null; review_status: string; review_notes: string | null }
interface Detail { id: string; full_name: string; phone: string; email: string | null; status: string; capacity_per_week: number; interview_at: string | null; induction_completed_at: string | null; trial_job_completed_at: string | null; documents: Doc[]; verification: { checks: Record<string, boolean>; ready: boolean } }

export default function ProviderPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const { data: p, loading, error, reload } = useFetch<Detail>(`/admin/providers/${id}`);
  const a = useAction();
  const file = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState("identity");
  const [last4, setLast4] = useState("");
  const [exp, setExp] = useState("");
  if (!p) return <State loading={loading} error={error} />;
  const act = (fn: () => Promise<unknown>) => a.run(async () => { await fn(); reload(); });
  const now = () => new Date().toISOString();

  return (
    <>
      <PageHeader title={p.full_name} description={`${p.phone}${p.email ? " · " + p.email : ""}`} actions={<StatusBadge status={p.status} />} />
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Verification checklist</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
          <ul>{Object.entries(p.verification.checks).map(([k, ok]) => <li key={k} className="flex items-center justify-between py-1"><span>{label(k.replace(":", " – "))}</span><StatusBadge status={ok ? "approved" : "pending"} /></li>)}</ul>
          <dl><KV k="Interview" v={fmtDate(p.interview_at, false)} /><KV k="Induction" v={fmtDate(p.induction_completed_at, false)} /><KV k="Trial job" v={fmtDate(p.trial_job_completed_at, false)} /></dl>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => act(() => patch(`/admin/providers/${id}`, { interview_at: now() }))}>Mark interview done</Button>
            <Button size="sm" variant="outline" onClick={() => act(() => patch(`/admin/providers/${id}`, { induction_completed_at: now() }))}>Mark induction done</Button>
            <Button size="sm" variant="outline" onClick={() => act(() => patch(`/admin/providers/${id}`, { trial_job_completed_at: now() }))}>Mark trial job done</Button>
          </div>
          {me?.role === "admin" && <div className="flex flex-wrap gap-2 border-t pt-3">
            <Button size="sm" variant="accent" disabled={!p.verification.ready || p.status === "verified"} onClick={() => act(() => post(`/admin/providers/${id}/status`, { status: "verified" }))}>Mark verified</Button>
            <Button size="sm" variant="destructive" onClick={() => { const reason = prompt("Reason for suspension?"); if (reason) act(() => post(`/admin/providers/${id}/status`, { status: "suspended", reason })); }}>Suspend</Button>
          </div>}
        </CardContent></Card>

        <Card><CardHeader><CardTitle>Documents</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
          <ul className="divide-y">{p.documents.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-2"><span>{label(d.doc_type)} · {d.filename}{d.reference_last4 ? ` (…${d.reference_last4})` : ""}{d.expires_at ? ` · exp ${fmtDate(d.expires_at, false)}` : ""}</span>
              <span className="flex items-center gap-1.5"><StatusBadge status={d.review_status} />
                <Button size="sm" variant="outline" onClick={async () => { const { url } = await get<{ url: string }>(`/admin/providers/documents/${d.id}/url`); window.open(url, "_blank", "noopener"); }}>View</Button>
                {me?.role === "admin" && d.review_status === "pending" && <><Button size="sm" variant="accent" onClick={() => act(() => post(`/admin/providers/documents/${d.id}/review`, { decision: "approved" }))}>Approve</Button><Button size="sm" variant="destructive" onClick={() => { const notes = prompt("Reason?"); if (notes) act(() => post(`/admin/providers/documents/${d.id}/review`, { decision: "rejected", notes })); }}>Reject</Button></>}</span></li>))}</ul>
          <form className="grid gap-2 border-t pt-3" onSubmit={(e) => { e.preventDefault(); const f = file.current?.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); fd.append("doc_type", docType); if (last4) fd.append("reference_last4", last4); if (exp) fd.append("expires_at", new Date(exp).toISOString()); act(async () => { await api(`/admin/providers/${id}/documents`, { form: fd }); if (file.current) file.current.value = ""; }); }}>
            <div className="grid gap-2 sm:grid-cols-3"><Field label="Type"><Select value={docType} onChange={(e) => setDocType(e.target.value)}>{["identity", "address", "reference", "licence", "insurance", "police_verification", "other"].map((t) => <option key={t} value={t}>{label(t)}</option>)}</Select></Field>
              <Field label="ID last 4 (never full number)"><Input maxLength={4} value={last4} onChange={(e) => setLast4(e.target.value)} /></Field><Field label="Expiry"><Input type="date" value={exp} onChange={(e) => setExp(e.target.value)} /></Field></div>
            <input ref={file} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required className="text-sm" />
            <Button size="sm" type="submit" disabled={a.busy}>Upload document</Button>
          </form>
        </CardContent></Card>
      </div>
    </>
  );
}
