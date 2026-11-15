"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Select, Textarea } from "@/components/ui/form";
import { KV, PageHeader, State } from "@/components/common";
import { patch } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate, label } from "@/lib/utils";

interface D { id: string; reference: string; request_id: string | null; category: string; severity: string; status: string; description: string; event_time: string; reporter_role: string; escalation_contacts: string[]; actions_taken: string | null; customer_communication: string | null; closure_review: string | null; notes: { id: string; note: string; created_at: string }[] }

export default function IncidentPage() {
  const { id } = useParams<{ id: string }>();
  const { data: i, loading, error, reload } = useFetch<D>(`/admin/incidents/${id}`);
  const a = useAction();
  const [f, setF] = useState({ status: "open", severity: "medium", actions_taken: "", customer_communication: "", closure_review: "", escalation: "", note: "" });
  useEffect(() => { if (i) setF({ status: i.status, severity: i.severity, actions_taken: i.actions_taken ?? "", customer_communication: i.customer_communication ?? "", closure_review: i.closure_review ?? "", escalation: i.escalation_contacts.join(", "), note: "" }); }, [i]);
  if (!i) return <State loading={loading} error={error} />;
  return (
    <>
      <PageHeader title={i.reference} description={`${label(i.category)} · reported by ${i.reporter_role} · ${fmtDate(i.event_time)}`} actions={<><StatusBadge status={i.severity} /><StatusBadge status={i.status} /></>} />
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>What happened</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><p>{i.description}</p>{i.request_id && <Link className="text-accent hover:underline" href={`/admin/requests/${i.request_id}`}>Open linked request →</Link>}
          <h3 className="pt-2 font-semibold">Notes</h3><ul className="space-y-2">{i.notes.map((n) => <li key={n.id}><div className="text-xs text-muted-foreground">{fmtDate(n.created_at)}</div>{n.note}</li>)}</ul></CardContent></Card>
        <Card><CardHeader><CardTitle>Handling</CardTitle></CardHeader><CardContent className="grid gap-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Status"><Select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>{["open", "investigating", "resolved", "closed"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select></Field>
            <Field label="Severity"><Select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })}>{["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select></Field>
          </div>
          <Field label="Escalation contacts (comma separated)"><input className="min-h-10 rounded-md border border-input bg-card px-3 text-sm" value={f.escalation} onChange={(e) => setF({ ...f, escalation: e.target.value })} /></Field>
          <Field label="Actions taken"><Textarea className="min-h-16" value={f.actions_taken} onChange={(e) => setF({ ...f, actions_taken: e.target.value })} /></Field>
          <Field label="Family communication"><Textarea className="min-h-16" value={f.customer_communication} onChange={(e) => setF({ ...f, customer_communication: e.target.value })} /></Field>
          <Field label="Closure review (required to close)"><Textarea className="min-h-16" value={f.closure_review} onChange={(e) => setF({ ...f, closure_review: e.target.value })} /></Field>
          <Field label="Add note"><Textarea className="min-h-16" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
          <Button disabled={a.busy} onClick={() => a.run(async () => { await patch(`/admin/incidents/${id}`, { status: f.status, severity: f.severity, actions_taken: f.actions_taken || null, customer_communication: f.customer_communication || null, closure_review: f.closure_review || null, escalation_contacts: f.escalation.split(",").map((s) => s.trim()).filter(Boolean), note: f.note || undefined }); reload(); })}>Save</Button>
        </CardContent></Card>
      </div>
    </>
  );
}
