"use client";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { PageHeader, Stat, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import { label } from "@/lib/utils";

interface Overview {
  open_requests: number; new_requests: number; awaiting_quote: number; awaiting_customer_approval: number; jobs_today: number;
  open_incidents: number; verified_providers: number; providers_in_verification: number;
  overdue: { id: string; reference: string; status: string }[]; by_status: Record<string, number>;
}

export default function Overview() {
  const { data, loading, error } = useFetch<Overview>("/admin/overview");
  if (!data) return <State loading={loading} error={error} />;
  return (
    <>
      <PageHeader title="Operations overview" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Open requests" value={data.open_requests} href="/admin/requests" />
        <Stat label="New (unreviewed)" value={data.new_requests} href="/admin/requests?status=new_request" tone={data.new_requests ? "warn" : undefined} />
        <Stat label="Awaiting quote" value={data.awaiting_quote} href="/admin/requests?status=quote_pending" />
        <Stat label="Awaiting customer approval" value={data.awaiting_customer_approval} href="/admin/requests?status=approval_pending" />
        <Stat label="Jobs today" value={data.jobs_today} />
        <Stat label="Overdue" value={data.overdue.length} tone={data.overdue.length ? "bad" : undefined} />
        <Stat label="Open incidents" value={data.open_incidents} href="/admin/incidents" tone={data.open_incidents ? "bad" : undefined} />
        <Stat label="Verified providers" value={`${data.verified_providers} (+${data.providers_in_verification} pending)`} href="/admin/providers" />
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Overdue requests</CardTitle></CardHeader><CardContent>
          {data.overdue.length === 0 ? <p className="text-sm text-muted-foreground">Nothing overdue.</p> : <ul className="divide-y text-sm">{data.overdue.map((o) => <li key={o.id} className="flex justify-between py-2"><Link className="text-accent hover:underline" href={`/admin/requests/${o.id}`}>{o.reference}</Link><StatusBadge status={o.status} /></li>)}</ul>}
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Requests by status</CardTitle></CardHeader><CardContent><ul className="grid grid-cols-2 gap-x-6 text-sm">
          {Object.entries(data.by_status).filter(([, n]) => n > 0).map(([s, n]) => <li key={s} className="flex justify-between py-1"><span>{label(s)}</span><strong>{n}</strong></li>)}
        </ul></CardContent></Card>
      </div>
    </>
  );
}
