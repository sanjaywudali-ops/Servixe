"use client";
import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction, useFetch } from "@/lib/hooks";
import type { Invoice } from "@/lib/types";
import { fmtDate, money } from "@/lib/utils";

interface Payout { id: string; provider_id: string; request_id: string; amount_minor: number; currency: string; status: string; paid_at: string | null; payment_reference: string | null }

export default function Finance() {
  const { me } = useAuth();
  const inv = useFetch<Invoice[]>("/admin/invoices");
  const pay = useFetch<Payout[]>("/admin/payouts");
  const a = useAction();
  const [tab, setTab] = useState<"inv" | "pay">("inv");
  const act = (fn: () => Promise<unknown>) => a.run(async () => { await fn(); inv.reload(); pay.reload(); });
  return (
    <>
      <PageHeader title="Finance" description="Quotes, invoices, payment reconciliation, refunds and provider payouts." />
      <div className="mb-4 flex gap-2"><Button variant={tab === "inv" ? "default" : "outline"} size="sm" onClick={() => setTab("inv")}>Invoices</Button><Button variant={tab === "pay" ? "default" : "outline"} size="sm" onClick={() => setTab("pay")}>Provider payouts</Button></div>
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      {tab === "inv" ? (<>
        <State loading={inv.loading} error={inv.error} empty={inv.data?.length === 0} emptyText="No invoices yet." />
        {inv.data && inv.data.length > 0 && <Table><THead><tr><TH>Invoice</TH><TH>Request</TH><TH>Total</TH><TH>Issued</TH><TH>Paid</TH><TH>Status</TH><TH></TH></tr></THead><tbody>
          {inv.data.map((i) => <TR key={i.id}><TD>{i.number}</TD><TD><Link className="text-accent hover:underline" href={`/admin/requests/${i.request_id}`}>Open</Link></TD><TD>{money(i.total_minor, i.currency)}</TD><TD>{fmtDate(i.issued_at, false)}</TD><TD>{fmtDate(i.paid_at, false)}</TD><TD><StatusBadge status={i.status} /></TD>
            <TD>{i.status === "draft" && <Button size="sm" onClick={() => act(() => post(`/admin/invoices/${i.id}/issue`))}>Issue</Button>}</TD></TR>)}
        </tbody></Table>}
      </>) : (<>
        <State loading={pay.loading} error={pay.error} empty={pay.data?.length === 0} emptyText="No payouts yet. Payouts are created when a job passes quality review." />
        {pay.data && pay.data.length > 0 && <Table><THead><tr><TH>Request</TH><TH>Amount</TH><TH>Status</TH><TH>Paid</TH><TH>Reference</TH><TH></TH></tr></THead><tbody>
          {pay.data.map((p) => <TR key={p.id}><TD><Link className="text-accent hover:underline" href={`/admin/requests/${p.request_id}`}>Open</Link></TD><TD>{money(p.amount_minor, p.currency)}</TD><TD><StatusBadge status={p.status} /></TD><TD>{fmtDate(p.paid_at, false)}</TD><TD>{p.payment_reference ?? "—"}</TD>
            <TD>{me?.role === "admin" && <span className="flex gap-1.5">{p.status === "pending" && <Button size="sm" onClick={() => act(() => patch(`/admin/payouts/${p.id}`, { status: "approved" }))}>Approve</Button>}{p.status === "approved" && <Button size="sm" variant="accent" onClick={() => { const ref = prompt("Bank/UPI payment reference?"); if (ref) act(() => patch(`/admin/payouts/${p.id}`, { status: "paid", payment_reference: ref })); }}>Mark paid</Button>}{p.status !== "paid" && p.status !== "on_hold" && <Button size="sm" variant="ghost" onClick={() => act(() => patch(`/admin/payouts/${p.id}`, { status: "on_hold" }))}>Hold</Button>}</span>}</TD></TR>)}
        </tbody></Table>}
      </>)}
    </>
  );
}
