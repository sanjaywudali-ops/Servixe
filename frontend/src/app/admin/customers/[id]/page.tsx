"use client";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { KV, PageHeader, State } from "@/components/common";
import { post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { Authorisation, Consent, Parent } from "@/lib/types";
import { fmtDate, label, localToIso } from "@/lib/utils";

interface Cust { id: string; full_name: string; email: string; country: string; phone: string | null; whatsapp_opt_in: boolean; parents: (Parent & { authorisation: Authorisation })[] }
const SCOPES = ["home_visit", "errands", "photographs", "updates", "information_sharing"];

function ConsentPanel({ parent, onDone }: { parent: Parent & { authorisation: Authorisation }; onDone: () => void }) {
  const consents = useFetch<Consent[]>(`/admin/parents/${parent.id}/consents`);
  const [scopes, setScopes] = useState<string[]>(["home_visit", "updates"]);
  const [f, setF] = useState({ given_by: parent.full_name, captured_via: "in_person", evidence_ref: "", notes: "", valid_until: "" });
  const [perm, setPerm] = useState({ can_request_services: true, can_receive_updates: true, can_approve_costs: true, can_view_evidence: false });
  const a = useAction();
  const active = consents.data?.find((c) => !c.revoked_at);

  const record = () => a.run(async () => {
    await post(`/admin/parents/${parent.id}/consents`, { scopes, given_by: f.given_by, captured_via: f.captured_via, evidence_ref: f.evidence_ref || null, notes: f.notes || null, valid_until: localToIso(f.valid_until) ?? null });
    consents.reload(); onDone();
  });
  const activate = (consentId: string) => a.run(async () => { await post(`/admin/authorisations/${parent.authorisation.id}/activate`, { consent_id: consentId, ...perm }); onDone(); });

  return (
    <div className="mt-3 space-y-4 rounded-md border bg-muted/40 p-4 text-sm">
      {a.error && <Alert tone="error">{a.error}</Alert>}
      <div>
        <h4 className="font-semibold">Consent records</h4>
        {consents.data?.length ? <ul className="mt-1 space-y-1.5">{consents.data.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-1.5">{c.scopes.map((s) => <Badge key={s}>{label(s)}</Badge>)}<span className="text-xs text-muted-foreground">{c.given_by} · {label(c.captured_via)} · {fmtDate(c.captured_at, false)}</span>
            {c.revoked_at ? <Badge tone="danger">revoked</Badge> : <Button size="sm" variant="ghost" onClick={() => { const reason = prompt("Reason for revoking?"); if (reason) a.run(async () => { await post(`/admin/consents/${c.id}/revoke`, { reason }); consents.reload(); onDone(); }); }}>Revoke</Button>}</li>))}</ul> : <p className="text-muted-foreground">None.</p>}
      </div>
      <div className="grid gap-3 border-t pt-3">
        <h4 className="font-semibold">Record parent’s informed agreement</h4>
        <div className="flex flex-wrap gap-3">{SCOPES.map((s) => <label key={s} className="flex items-center gap-1.5"><input type="checkbox" checked={scopes.includes(s)} onChange={(e) => setScopes(e.target.checked ? [...scopes, s] : scopes.filter((x) => x !== s))} />{label(s)}</label>)}</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Given by"><Input value={f.given_by} onChange={(e) => setF({ ...f, given_by: e.target.value })} /></Field>
          <Field label="How captured"><Select value={f.captured_via} onChange={(e) => setF({ ...f, captured_via: e.target.value })}>{["in_person", "phone_call", "signed_form", "video_call", "other"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select></Field>
          <Field label="Reference (form no. / call ref)"><Input value={f.evidence_ref} onChange={(e) => setF({ ...f, evidence_ref: e.target.value })} /></Field>
          <Field label="Valid until (optional)"><Input type="datetime-local" value={f.valid_until} onChange={(e) => setF({ ...f, valid_until: e.target.value })} /></Field>
        </div>
        <Field label="Notes"><Textarea className="min-h-16" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        <Button size="sm" disabled={a.busy || scopes.length === 0} onClick={record}>Save consent record</Button>
      </div>
      {parent.authorisation.status !== "active" && (
        <div className="grid gap-2 border-t pt-3">
          <h4 className="font-semibold">Activate customer’s authorisation</h4>
          <div className="flex flex-wrap gap-3">{(Object.keys(perm) as (keyof typeof perm)[]).map((k) => <label key={k} className="flex items-center gap-1.5"><input type="checkbox" checked={perm[k]} onChange={(e) => setPerm({ ...perm, [k]: e.target.checked })} />{label(k.replace("can_", ""))}</label>)}</div>
          <Button size="sm" variant="accent" disabled={!active || a.busy} onClick={() => active && activate(active.id)}>{active ? "Activate using latest consent" : "Record a consent first"}</Button>
        </div>
      )}
    </div>
  );
}

export default function CustomerPage() {
  const { id } = useParams<{ id: string }>();
  const { data: c, loading, error, reload } = useFetch<Cust>(`/admin/customers/${id}`);
  const [open, setOpen] = useState<string | null>(null);
  if (!c) return <State loading={loading} error={error} />;
  return (
    <>
      <PageHeader title={c.full_name} description="Customer (payer) record — kept separate from the parent (service recipient)." />
      <Card className="mb-5 max-w-xl"><CardContent className="pt-5"><dl><KV k="Email" v={c.email} /><KV k="Country" v={c.country} /><KV k="Phone" v={c.phone} /><KV k="WhatsApp opt-in" v={c.whatsapp_opt_in ? "Yes" : "No"} /></dl></CardContent></Card>
      <h2 className="mb-3 text-lg font-semibold">Parents &amp; authorisations</h2>
      <div className="space-y-4">{c.parents.map((p) => (
        <Card key={p.id}><CardHeader className="flex-row items-center justify-between"><CardTitle>{p.full_name} <span className="font-normal text-muted-foreground">· {[p.area, p.city].filter(Boolean).join(", ")}</span></CardTitle><div className="flex items-center gap-2"><StatusBadge status={p.authorisation.status} /><Button size="sm" variant="outline" onClick={() => setOpen(open === p.id ? null : p.id)}>Consent &amp; authority</Button></div></CardHeader>
          <CardContent><p className="text-sm text-muted-foreground">Relationship: {p.authorisation.relationship_to_parent} · {p.phone ?? "no phone"}</p>{open === p.id && <ConsentPanel parent={p} onDone={reload} />}</CardContent></Card>
      ))}</div>
    </>
  );
}
