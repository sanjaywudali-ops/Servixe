"use client";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { Phone } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { EMERGENCY_TEXT, KV, State } from "@/components/common";
import { api, post, put } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { JobView } from "@/lib/types";
import { fmtDate, label, money } from "@/lib/utils";

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: j, loading, error, reload } = useFetch<JobView>(`/provider/jobs/${id}`);
  const a = useAction();
  const file = useRef<HTMLInputElement>(null);
  const [purpose, setPurpose] = useState("completion_photo");
  const [msg, setMsg] = useState<string | null>(null);
  const [inc, setInc] = useState({ open: false, severity: "medium", category: "safety", description: "" });
  if (!j) return <State loading={loading} error={error} />;
  const act = (fn: () => Promise<unknown>) => a.run(async () => { await fn(); reload(); });
  const cl = j.checklist;
  const inProgress = j.request_status === "in_progress";
  const toggle = (key: string, done: boolean) => act(() => put(`/provider/jobs/${id}/checklist`, { responses: { ...(cl?.responses ?? {}), [key]: { done } } }));

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between"><div><h1 className="text-xl font-bold">{j.service}</h1><p className="text-sm text-muted-foreground">{j.reference}</p></div><StatusBadge status={j.status} /></div>
      {a.error && <Alert tone="error">{a.error}</Alert>}
      {msg && <Alert tone="success">{msg}</Alert>}

      <Card><CardContent className="pt-5"><dl>
        <KV k="When" v={`${fmtDate(j.window_start)} → ${fmtDate(j.window_end)}`} /><KV k="Area" v={j.area} /><KV k="Payout" v={money(j.payout_minor, j.currency)} />
        {j.status === "accepted" && <>
          <KV k="Parent" v={j.parent_first_name} /><KV k="Address" v={j.location} /><KV k="Task" v={j.task_details} /><KV k="Instructions" v={j.instructions} />
          {j.contact_phone && <KV k="Contact" v={<a className="inline-flex items-center gap-1 text-accent" href={`tel:${j.contact_phone}`}><Phone className="h-4 w-4" />{j.contact_phone}</a>} />}
        </>}
      </dl>{j.status === "offered" && <p className="mt-2 text-xs text-muted-foreground">Address and contact details are shown after you accept.</p>}</CardContent></Card>

      {j.status === "offered" && (
        <div className="grid grid-cols-2 gap-3">
          <Button size="lg" variant="accent" disabled={a.busy} onClick={() => act(() => post(`/provider/jobs/${id}/accept`))}>Accept job</Button>
          <Button size="lg" variant="outline" disabled={a.busy} onClick={() => { const reason = prompt("Reason for declining?"); if (reason && reason.length >= 3) act(() => post(`/provider/jobs/${id}/reject`, { reason })); }}>Decline</Button>
        </div>
      )}

      {j.status === "accepted" && j.role === "primary" && !j.checked_in_at && <Button size="lg" className="w-full" variant="accent" disabled={a.busy} onClick={() => act(() => post(`/provider/jobs/${id}/check-in`, {}))}>Check in</Button>}
      {j.status === "accepted" && j.role === "backup" && <Alert>You’re the backup provider. You’ll be notified if you’re promoted to primary.</Alert>}
      {j.checked_in_at && <p className="text-sm text-muted-foreground">Checked in {fmtDate(j.checked_in_at)}{j.checked_out_at ? ` · out ${fmtDate(j.checked_out_at)}` : ""}</p>}

      {cl && cl.items.length > 0 && (
        <Card><CardHeader><CardTitle>Checklist</CardTitle></CardHeader><CardContent><ul className="space-y-2">
          {cl.items.map((it) => (
            <li key={it.key}><label className="flex min-h-10 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5" disabled={!inProgress || a.busy} checked={!!cl.responses[it.key]?.done} onChange={(e) => toggle(it.key, e.target.checked)} />{it.label}{it.required === false && <span className="text-xs text-muted-foreground">(optional)</span>}</label></li>))}
        </ul>{cl.completed_at && <p className="mt-2 text-xs text-success">Required items complete.</p>}</CardContent></Card>
      )}

      {inProgress && (
        <Card><CardHeader><CardTitle>Upload evidence</CardTitle></CardHeader><CardContent>
          <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); const f = file.current?.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); fd.append("purpose", purpose); act(async () => { await api(`/provider/jobs/${id}/evidence`, { form: fd }); if (file.current) file.current.value = ""; setMsg("Uploaded."); }); }}>
            <Field label="Type"><Select value={purpose} onChange={(e) => setPurpose(e.target.value)}><option value="completion_photo">Completion photo</option><option value="receipt">Receipt</option><option value="document">Document</option></Select></Field>
            <input ref={file} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" capture="environment" required className="text-sm" />
            <p className="text-xs text-muted-foreground">Photos are allowed only where the parent has agreed. Do not photograph anything beyond the task.</p>
            <Button type="submit" disabled={a.busy}>Upload</Button>
          </form>
          {j.evidence && j.evidence.length > 0 && <p className="mt-2 text-xs text-muted-foreground">{j.evidence.length} file(s) uploaded.</p>}
        </CardContent></Card>
      )}

      {inProgress && <Button size="lg" className="w-full" disabled={a.busy} onClick={() => act(() => post(`/provider/jobs/${id}/check-out`, {}))}>Check out &amp; finish</Button>}
      {j.request_status === "quality_check" && <Alert tone="success">Thanks — Servixe is reviewing this job.</Alert>}

      {["accepted"].includes(j.status) && (
        <Card><CardHeader><CardTitle>Report an incident or urgent concern</CardTitle></CardHeader><CardContent className="space-y-3">
          <Alert tone="error">{EMERGENCY_TEXT} Contact emergency services first if anyone is in danger, then report here.</Alert>
          {!inc.open ? <Button variant="outline" onClick={() => setInc({ ...inc, open: true })}>Report incident</Button> : (
            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Category"><Select value={inc.category} onChange={(e) => setInc({ ...inc, category: e.target.value })}>{["safety", "complaint", "missed_visit", "other"].map((c) => <option key={c} value={c}>{label(c)}</option>)}</Select></Field>
                <Field label="Severity"><Select value={inc.severity} onChange={(e) => setInc({ ...inc, severity: e.target.value })}>{["low", "medium", "high", "critical"].map((c) => <option key={c} value={c}>{label(c)}</option>)}</Select></Field>
              </div>
              <Field label="What happened?"><Textarea value={inc.description} onChange={(e) => setInc({ ...inc, description: e.target.value })} /></Field>
              <Button variant="destructive" disabled={a.busy || inc.description.length < 5} onClick={() => act(async () => { const r = await post<{ reference: string }>(`/provider/jobs/${id}/incident`, { category: inc.category, severity: inc.severity, description: inc.description }); setMsg(`Reported as ${r.reference}. Our team will respond.`); setInc({ open: false, severity: "medium", category: "safety", description: "" }); })}>Submit report</Button>
            </div>)}
        </CardContent></Card>
      )}
    </div>
  );
}
