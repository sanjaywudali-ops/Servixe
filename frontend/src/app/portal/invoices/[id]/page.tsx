"use client";
import { useParams } from "next/navigation";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { KV, PageHeader, State } from "@/components/common";
import { post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { Invoice } from "@/lib/types";
import { fmtDate, money } from "@/lib/utils";

export default function InvoicePage() {
  const { id } = useParams<{ id: string }>();
  const { data: i, loading, error } = useFetch<Invoice>(`/portal/invoices/${id}`);
  const a = useAction();
  if (!i) return <State loading={loading} error={error} />;
  return (
    <>
      <PageHeader title={`Invoice ${i.number}`} actions={<StatusBadge status={i.status} />} />
      <Card className="max-w-xl"><CardHeader><CardTitle>Summary</CardTitle></CardHeader><CardContent>
        <dl><KV k="Provider / third-party charges" v={money(i.provider_cost_minor, i.currency)} /><KV k="Coordination fee" v={money(i.coordination_fee_minor, i.currency)} /><KV k="Taxes" v={money(i.tax_minor, i.currency)} /><KV k="Total" v={<strong>{money(i.total_minor, i.currency)}</strong>} /><KV k="Due" v={fmtDate(i.due_at, false)} /><KV k="Paid" v={i.paid_at ? fmtDate(i.paid_at) : null} /></dl>
        {i.status === "issued" && <div className="mt-4"><Button variant="accent" disabled={a.busy} onClick={() => a.run(async () => { const r = await post<{ checkout_url: string }>(`/portal/invoices/${id}/checkout`); window.location.href = r.checkout_url; })}>Pay securely</Button><p className="mt-2 text-xs text-muted-foreground">You’ll be taken to a hosted checkout. Servixe never sees or stores your card details.</p></div>}
        {a.error && <Alert tone="error" className="mt-3">{a.error}</Alert>}
        {i.payments && i.payments.length > 0 && <><h3 className="mt-5 text-sm font-semibold">Payments</h3><ul className="text-sm">{i.payments.map((p) => <li key={p.id} className="flex justify-between py-1"><span>{fmtDate(p.created_at)}</span><span>{money(p.amount_minor, i.currency)} <StatusBadge status={p.status} /></span></li>)}</ul></>}
        {i.refunds && i.refunds.length > 0 && <><h3 className="mt-5 text-sm font-semibold">Refunds</h3><ul className="text-sm">{i.refunds.map((r) => <li key={r.id} className="flex justify-between py-1"><span>{r.reason}</span><span>{money(r.amount_minor, i.currency)} <StatusBadge status={r.status} /></span></li>)}</ul></>}
      </CardContent></Card>
    </>
  );
}
