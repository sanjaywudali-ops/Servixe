"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { KV, PageHeader, State } from "@/components/common";
import { del as api_delete, get, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction, useFetch } from "@/lib/hooks";
import type { EvidenceItem } from "@/lib/types";
import { fmtDate, label, money, toMinor } from "@/lib/utils";

interface Detail {
  id: string; reference: string; status: string; priority: string; service_name: string; parent_name: string; parent_id: string; task_details: string; location_text: string | null;
  requested_start: string | null; requested_end: string | null; budget_cap_minor: number | null; currency: string; customer_id: string; consent_scope: string | null;
  approval_exception_reason: string | null; quality_outcome: string | null; quality_notes: string | null; internal_notes: string | null; allowed_transitions: string[];
  timeline: { id: string; event_type: string; from_status: string | null; to_status: string | null; message: string | null; visible_to_customer: boolean; created_at: string }[];
  quotes: { id: string; version: number; status: string; total_minor: number; provider_cost_minor: number; currency: string; exceeds_budget_cap: boolean; valid_until: string | null }[];
  assignments: { id: string; provider_id: string; provider_name: string; role: string; status: string; reject_reason: string | null; checked_in_at: string | null; checked_out_at: string | null; provider_payout_minor: number }[];
}
interface Prov { id: string; full_name: string; phone: string }
interface Inv { id: string; number: string; status: string; request_id: string; total_minor: number; currency: string }

export default function RequestWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const { data: r, loading, error, reload } = useFetch<Detail>(`/admin/requests/${id}`);
  const provs = useFetch<Prov[]>(`/admin/providers/suggest/${id}`);
  const evid = useFetch<EvidenceItem[]>(`/admin/requests/${id}/evidence`);
  const invs = useFetch<Inv[]>("/admin/invoices");
  const a = useAction();
  const [note, setNote] = useState({ message: "", visible: false });
  const [quote, setQuote] = useState({ scope_summary: "", provider_cost: "" });
  const [assign, setAssign] = useState({ provider_id: "", role: "primary", payout: "", instructions: "" });
  const [qr, setQr] = useState({ outcome: "pass", notes: "", customer_message: "" });
  useEffect(() => { if (r && !quote.scope_summary) setQuote((q) => ({ ...q, scope_summary: r.task_details })); }, [r]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!r) return <State loading={loading} error={error} />;

  const act = (fn: () => Promise<unknown>) => a.run(async () => { await fn(); reload(); evid.reload(); invs.reload(); provs.reload(); });
  const inv = invs.data?.find((i) => i.request_id === r.id && i.status !== "void");
  const canQuote = ["under_review", "quote_pending", "approval_pending", "assigned", "in_progress"].includes(r.status);
  const canAssign = ["under_review", "approval_pending", "assigned"].includes(r.status);
  const simple = r.allowed_transitions.filter((t) => !["assigned", "in_progress", "quality_check", "completed", "approval_pending"].includes(t));

  return (
    <>
      <PageHeader title={`${r.reference} · ${r.service_name}`} description={`${r.parent_name} · ${label(r.priority)} priority`} actions={<StatusBadge status={r.status} />} />
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card><CardHeader><CardTitle>Request</CardTitle></CardHeader><CardContent><dl>
            <KV k="Task" v={r.task_details} /><KV k="Location" v={r.location_text} /><KV k="Window" v={`${fmtDate(r.requested_start)} → ${fmtDate(r.requested_end)}`} />
            <KV k="Budget cap" v={r.budget_cap_minor != null ? money(r.budget_cap_minor, r.currency) : null} /><KV k="Required consent" v={label(r.consent_scope)} />
            {r.approval_exception_reason && <KV k="Approval exception" v={<span className="text-warning">{r.approval_exception_reason}</span>} />}
            {r.quality_outcome && <KV k="Quality review" v={`${label(r.quality_outcome)} ${r.quality_notes ? "— " + r.quality_notes : ""}`} />}
          </dl></CardContent></Card>

          <Card><CardHeader><CardTitle>Workflow</CardTitle></CardHeader><CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">Status changes are validated by the server: consent, approval, checklist, quality and invoice gates cannot be skipped.</p>
            <div className="flex flex-wrap gap-2">{simple.map((t) => <Button key={t} size="sm" variant={["cancelled", "rejected"].includes(t) ? "destructive" : "outline"} disabled={a.busy} onClick={() => { const needs = ["cancelled", "rejected"].includes(t); const n = needs ? prompt(`Reason for ${label(t).toLowerCase()}?`) : ""; if (needs && !n) return; act(() => post(`/admin/requests/${id}/transition`, { to_status: t, note: n || undefined, notify_customer: needs })); }}>{label(t)}</Button>)}
              {simple.length === 0 && <span className="text-sm text-muted-foreground">No manual transitions available from this status.</span>}</div>
            {me?.role === "admin" && !r.approval_exception_reason && <Button size="sm" variant="ghost" onClick={() => { const reason = prompt("Documented reason for approval exception (admin only, audited):"); if (reason && reason.length >= 10) act(() => post(`/admin/requests/${id}/approval-exception`, { reason })); }}>Grant approval exception…</Button>}
          </CardContent></Card>

          {canQuote && <Card><CardHeader><CardTitle>Quote</CardTitle></CardHeader><CardContent className="space-y-3">
            <ul className="text-sm">{r.quotes.map((q) => <li key={q.id} className="flex items-center justify-between border-b py-1.5"><span>v{q.version} · {money(q.total_minor, q.currency)} {q.exceeds_budget_cap && <span className="text-xs text-warning">(over cap)</span>}</span><StatusBadge status={q.status} /></li>)}</ul>
            <Field label="Scope summary"><Textarea className="min-h-20" value={quote.scope_summary} onChange={(e) => setQuote({ ...quote, scope_summary: e.target.value })} /></Field>
            <Field label={`Provider / third-party cost (${r.currency})`} hint="The coordination fee and tax are added from the pricing rules."><Input type="number" min="0" step="0.01" value={quote.provider_cost} onChange={(e) => setQuote({ ...quote, provider_cost: e.target.value })} /></Field>
            <Button size="sm" variant="accent" disabled={a.busy || quote.scope_summary.length < 5 || quote.provider_cost === ""} onClick={() => act(async () => { await post(`/admin/requests/${id}/quotes`, { scope_summary: quote.scope_summary, provider_cost_minor: toMinor(quote.provider_cost) }); setQuote({ scope_summary: r.task_details, provider_cost: "" }); })}>{r.quotes.length ? "Send revised quote (requires renewed approval)" : "Create & send quote"}</Button>
          </CardContent></Card>}

          <Card><CardHeader><CardTitle>Assignment</CardTitle></CardHeader><CardContent className="space-y-3">
            <ul className="divide-y text-sm">{r.assignments.map((x) => <li key={x.id} className="flex flex-wrap items-center justify-between gap-2 py-2"><span>{x.provider_name} · {label(x.role)}{x.reject_reason ? ` — declined: ${x.reject_reason}` : ""}</span><span className="flex items-center gap-2"><StatusBadge status={x.status} />{["offered", "accepted"].includes(x.status) && !x.checked_in_at && <Button size="sm" variant="ghost" onClick={() => act(() => api_delete(`/admin/assignments/${x.id}`))}>Withdraw</Button>}</span></li>)}</ul>
            {canAssign && <div className="grid gap-3 rounded-md border bg-muted/40 p-3 sm:grid-cols-2">
              <Field label="Verified provider"><Select value={assign.provider_id} onChange={(e) => setAssign({ ...assign, provider_id: e.target.value })}><option value="">Select…</option>{provs.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</Select></Field>
              <Field label="Role"><Select value={assign.role} onChange={(e) => setAssign({ ...assign, role: e.target.value })}><option value="primary">Primary</option><option value="backup">Backup</option></Select></Field>
              <Field label={`Provider payout (${r.currency})`}><Input type="number" min="0" step="0.01" value={assign.payout} onChange={(e) => setAssign({ ...assign, payout: e.target.value })} /></Field>
              <Field label="Approved task instructions (minimum necessary)" className="sm:col-span-2"><Textarea className="min-h-16" value={assign.instructions} onChange={(e) => setAssign({ ...assign, instructions: e.target.value })} /></Field>
              <Button size="sm" disabled={!assign.provider_id || a.busy} onClick={() => act(async () => { await post(`/admin/requests/${id}/assignments`, { provider_id: assign.provider_id, role: assign.role, provider_payout_minor: toMinor(assign.payout), instructions: assign.instructions || null }); setAssign({ provider_id: "", role: "primary", payout: "", instructions: "" }); })}>Assign</Button>
            </div>}
          </CardContent></Card>

          {r.status === "quality_check" && <Card><CardHeader><CardTitle>Quality review</CardTitle></CardHeader><CardContent className="grid gap-3">
            <Field label="Outcome"><Select value={qr.outcome} onChange={(e) => setQr({ ...qr, outcome: e.target.value })}><option value="pass">Pass</option><option value="pass_with_notes">Pass with notes</option><option value="fail">Fail — rework</option></Select></Field>
            <Field label="Internal notes"><Textarea className="min-h-16" value={qr.notes} onChange={(e) => setQr({ ...qr, notes: e.target.value })} /></Field>
            <Field label="Update to customer"><Textarea className="min-h-16" value={qr.customer_message} onChange={(e) => setQr({ ...qr, customer_message: e.target.value })} /></Field>
            <Button size="sm" variant="accent" disabled={a.busy} onClick={() => act(() => post(`/admin/requests/${id}/quality-review`, { outcome: qr.outcome, notes: qr.notes || null, customer_message: qr.customer_message || null }))}>Submit review</Button>
          </CardContent></Card>}

          <Card><CardHeader><CardTitle>Evidence</CardTitle></CardHeader><CardContent>
            {evid.data?.length ? <ul className="divide-y text-sm">{evid.data.map((e) => <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 py-2"><span>{e.caption || e.filename} <span className="text-xs text-muted-foreground">({label(e.purpose)})</span></span>
              <span className="flex items-center gap-2"><StatusBadge status={e.access_scope === "customer_visible" ? "active" : "pending"} /><Button size="sm" variant="outline" onClick={async () => { const { url } = await get<{ url: string }>(`/admin/evidence/${e.id}/url`); window.open(url, "_blank", "noopener"); }}>View</Button>
                <Button size="sm" variant="ghost" onClick={() => act(() => patch(`/admin/evidence/${e.id}`, { access_scope: e.access_scope === "customer_visible" ? "ops_only" : "customer_visible" }))}>{e.access_scope === "customer_visible" ? "Hide from customer" : "Release to customer"}</Button></span></li>)}</ul> : <p className="text-sm text-muted-foreground">No evidence uploaded.</p>}
            <p className="mt-2 text-xs text-muted-foreground">Viewing evidence is recorded in the audit trail.</p>
          </CardContent></Card>

          <Card><CardHeader><CardTitle>Billing</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">
            {inv ? <div className="flex items-center justify-between"><span>{inv.number} · {money(inv.total_minor, inv.currency)}</span><span className="flex items-center gap-2"><StatusBadge status={inv.status} />{inv.status === "draft" && <Button size="sm" onClick={() => act(() => post(`/admin/invoices/${inv.id}/issue`))}>Issue</Button>}{["draft", "issued"].includes(inv.status) && me?.role === "admin" && <Button size="sm" variant="outline" onClick={() => { const reason = prompt("Reason for waiving?"); if (reason) act(() => post(`/admin/invoices/${inv.id}/waive`, { reason })); }}>Waive</Button>}</span></div>
              : <Button size="sm" variant="outline" disabled={!["completed", "refund_pending"].includes(r.status)} onClick={() => act(() => post(`/admin/requests/${id}/invoice`))}>Create invoice from approved quote</Button>}
          </CardContent></Card>
        </div>

        <div className="space-y-5">
          <Card><CardHeader><CardTitle>Post an update</CardTitle></CardHeader><CardContent className="space-y-2">
            <Textarea className="min-h-20" value={note.message} onChange={(e) => setNote({ ...note, message: e.target.value })} />
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={note.visible} onChange={(e) => setNote({ ...note, visible: e.target.checked })} /> Visible to customer (sends a notification)</label>
            <Button size="sm" disabled={!note.message || a.busy} onClick={() => act(async () => { await post(`/admin/requests/${id}/updates`, { message: note.message, visible_to_customer: note.visible }); setNote({ message: "", visible: false }); })}>Add</Button>
          </CardContent></Card>
          <Card><CardHeader><CardTitle>Timeline &amp; audit</CardTitle></CardHeader><CardContent><ol className="space-y-3 text-sm">
            {[...r.timeline].reverse().map((e) => <li key={e.id}><div className="text-xs text-muted-foreground">{fmtDate(e.created_at)} · {label(e.event_type)}{e.visible_to_customer ? " · customer-visible" : ""}</div><div>{e.to_status && <strong>{label(e.to_status)} </strong>}{e.message}</div></li>)}
          </ol></CardContent></Card>
        </div>
      </div>
    </>
  );
}
