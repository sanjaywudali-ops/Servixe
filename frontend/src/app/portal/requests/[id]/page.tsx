"use client";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/form";
import { KV, PageHeader, State, Timeline } from "@/components/common";
import { get, post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { EvidenceItem, Quote, RequestSummary } from "@/lib/types";
import { fmtDate, label, money } from "@/lib/utils";

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const req = useFetch<RequestSummary>(`/portal/requests/${id}`);
  const quotes = useFetch<Quote[]>(`/portal/requests/${id}/quotes`);
  const evidence = useFetch<EvidenceItem[]>(`/portal/requests/${id}/evidence`);
  const [note, setNote] = useState("");
  const [concern, setConcern] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const { busy, error, run } = useAction();
  const r = req.data;
  if (!r) return <State loading={req.loading} error={req.error} />;
  const reloadAll = () => { req.reload(); quotes.reload(); };
  const pending = quotes.data?.find((q) => q.status === "pending");
  const canCancel = ["new_request", "under_review", "quote_pending", "approval_pending", "assigned"].includes(r.status);

  const decide = (q: Quote, decision: "approve" | "reject") => run(async () => { await post(`/portal/quotes/${q.id}/decision`, { decision, note: note || undefined }); setNote(""); reloadAll(); });
  const openEvidence = (e: EvidenceItem) => run(async () => { const { url } = await get<{ url: string }>(`/portal/evidence/${e.id}/url`); window.open(url, "_blank", "noopener"); });

  return (
    <>
      <PageHeader title={`${r.reference} · ${r.service_name}`} description={`For ${r.parent_name}`} actions={<StatusBadge status={r.status} />} />
      {error && <Alert tone="error" className="mb-4">{error}</Alert>}
      {notice && <Alert tone="success" className="mb-4">{notice}</Alert>}

      {pending && (
        <Card className="mb-5 border-accent">
          <CardHeader><CardTitle>Quote v{pending.version} — your approval is needed</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>{pending.scope_summary}</p>
            <dl className="max-w-sm">
              <KV k="Provider / third-party charges" v={money(pending.provider_cost_minor, pending.currency)} />
              <KV k="Servixe coordination fee" v={money(pending.coordination_fee_minor, pending.currency)} />
              <KV k="Taxes" v={money(pending.tax_minor, pending.currency)} />
              <KV k="Total" v={<strong>{money(pending.total_minor, pending.currency)}</strong>} />
              <KV k="Valid until" v={fmtDate(pending.valid_until)} />
            </dl>
            {pending.exceeds_budget_cap && <Alert tone="warning">This quote is above the budget limit you set ({money(r.budget_cap_minor, r.currency)}).</Alert>}
            <p className="text-xs text-muted-foreground">Cancellation terms: {pending.cancellation_terms}</p>
            <Textarea placeholder="Optional note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} className="min-h-16" />
            <div className="flex gap-2"><Button variant="accent" disabled={busy} onClick={() => decide(pending, "approve")}>Approve quote</Button><Button variant="outline" disabled={busy} onClick={() => decide(pending, "reject")}>Decline</Button></div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card><CardHeader><CardTitle>Details</CardTitle></CardHeader><CardContent><dl>
            <KV k="Task" v={r.task_details} /><KV k="Location" v={r.location_text} /><KV k="Requested" v={`${fmtDate(r.requested_start)} → ${fmtDate(r.requested_end)}`} />
            <KV k="Priority" v={label(r.priority)} /><KV k="Budget limit" v={r.budget_cap_minor != null ? money(r.budget_cap_minor, r.currency) : null} /><KV k="Completed" v={r.completed_at ? fmtDate(r.completed_at) : null} />
          </dl></CardContent></Card>

          {evidence.data && evidence.data.length > 0 && (
            <Card><CardHeader><CardTitle>Completion evidence</CardTitle></CardHeader><CardContent><ul className="divide-y text-sm">
              {evidence.data.map((e) => <li key={e.id} className="flex items-center justify-between py-2"><span>{e.caption || e.filename}</span><Button size="sm" variant="outline" onClick={() => openEvidence(e)}>View</Button></li>)}
            </ul><p className="mt-2 text-xs text-muted-foreground">Links are private and expire within minutes.</p></CardContent></Card>
          )}

          <Card><CardHeader><CardTitle>Raise a concern</CardTitle></CardHeader><CardContent className="space-y-2">
            <Textarea value={concern} onChange={(e) => setConcern(e.target.value)} placeholder="Tell us what went wrong or what worries you" maxLength={1500} />
            <Button variant="outline" disabled={busy || concern.trim().length < 3} onClick={() => run(async () => { const x = await post<{ reference: string }>(`/portal/requests/${id}/concern`, { message: concern }); setConcern(""); setNotice(`Thank you — we’ve logged your concern as ${x.reference}.`); })}>Send concern</Button>
            <p className="text-xs text-muted-foreground">For emergencies contact local emergency services (India: 112). Servixe is not an emergency service.</p>
          </CardContent></Card>

          {canCancel && <Button variant="destructive" size="sm" disabled={busy} onClick={() => { const reason = prompt("Reason for cancelling?"); if (reason && reason.length >= 3) run(async () => { await post(`/portal/requests/${id}/cancel`, { reason }); reloadAll(); }); }}>Cancel request</Button>}
        </div>
        <Card><CardHeader><CardTitle>Timeline</CardTitle></CardHeader><CardContent><Timeline events={r.timeline ?? []} /></CardContent></Card>
      </div>
    </>
  );
}
