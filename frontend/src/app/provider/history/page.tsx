"use client";
import { StatusBadge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import { fmtDate, money } from "@/lib/utils";

interface H { id: string; reference: string; service: string; status: string; request_status: string; completed_at: string | null; payout_status: string | null; payout_minor: number }

export default function History() {
  const { data, loading, error } = useFetch<H[]>("/provider/history");
  return (
    <>
      <PageHeader title="Job history & payouts" />
      <State loading={loading} error={error} empty={data?.length === 0} emptyText="No past jobs yet." />
      <div className="space-y-3">{data?.map((h) => (
        <Card key={h.id}><CardContent className="space-y-1 pt-5 text-sm">
          <div className="flex items-center justify-between"><span className="font-semibold">{h.service}</span><StatusBadge status={h.request_status} /></div>
          <div className="text-muted-foreground">{h.reference} · {fmtDate(h.completed_at, false)}</div>
          <div className="flex items-center justify-between"><span>Payout {money(h.payout_minor)}</span>{h.payout_status ? <StatusBadge status={h.payout_status} /> : <span className="text-xs text-muted-foreground">Not yet created</span>}</div>
        </CardContent></Card>))}</div>
    </>
  );
}
