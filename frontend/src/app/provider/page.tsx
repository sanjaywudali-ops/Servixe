"use client";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import type { JobView } from "@/lib/types";
import { fmtDate, money } from "@/lib/utils";

export default function Jobs() {
  const { data, loading, error } = useFetch<JobView[]>("/provider/jobs");
  const open = (data ?? []).filter((j) => !["completed", "rejected"].includes(j.status) && !["closed", "cancelled", "completed"].includes(j.request_status));
  return (
    <>
      <PageHeader title="My jobs" />
      <State loading={loading} error={error} empty={open.length === 0} emptyText="No active jobs right now." />
      <div className="space-y-3">{open.map((j) => (
        <Link key={j.id} href={`/provider/jobs/${j.id}`} className="block"><Card><CardContent className="space-y-1.5 pt-5">
          <div className="flex items-center justify-between"><span className="font-semibold">{j.service}</span><StatusBadge status={j.status} /></div>
          <div className="text-sm text-muted-foreground">{j.reference} · {j.role === "backup" ? "Backup" : "Primary"}</div>
          <div className="text-sm">{fmtDate(j.window_start)} → {fmtDate(j.window_end)}</div>
          <div className="text-sm text-muted-foreground">Area: {j.area ?? "—"} · Payout {money(j.payout_minor, j.currency)}</div>
        </CardContent></Card></Link>))}</div>
    </>
  );
}
