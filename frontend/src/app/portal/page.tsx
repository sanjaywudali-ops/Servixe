"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { PageHeader, State } from "@/components/common";
import { Alert } from "@/components/ui/alert";
import { useFetch } from "@/lib/hooks";
import type { Parent, RequestSummary } from "@/lib/types";
import { fmtDate } from "@/lib/utils";

export default function Dashboard() {
  const parents = useFetch<Parent[]>("/portal/parents");
  const reqs = useFetch<RequestSummary[]>("/portal/requests");
  const active = (reqs.data ?? []).filter((r) => !["closed", "cancelled", "rejected", "completed"].includes(r.status));
  const pending = (parents.data ?? []).filter((p) => p.authorisation?.status !== "active");
  return (
    <>
      <PageHeader title="Family dashboard" actions={<Button asChild variant="accent"><Link href="/portal/requests/new">New request</Link></Button>} />
      {pending.length > 0 && (
        <Alert tone="warning" className="mb-5">
          {pending.map((p) => p.full_name).join(", ")}: consent not yet recorded. Our team will contact your parent to record their informed agreement before services can begin.
        </Alert>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Parents</CardTitle></CardHeader>
          <CardContent>
            <State loading={parents.loading} error={parents.error} empty={parents.data?.length === 0} emptyText="Add your parent’s profile to get started." />
            <ul className="divide-y">{parents.data?.map((p) => (
              <li key={p.id} className="flex items-center justify-between py-2.5 text-sm"><Link href={`/portal/parents/${p.id}`} className="font-medium hover:text-accent">{p.full_name}</Link><StatusBadge status={p.authorisation?.status} /></li>
            ))}</ul>
            <Button asChild variant="outline" size="sm" className="mt-3"><Link href="/portal/parents/new">Add a parent</Link></Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Active requests</CardTitle></CardHeader>
          <CardContent>
            <State loading={reqs.loading} error={reqs.error} empty={active.length === 0} emptyText="No active requests." />
            <ul className="divide-y">{active.map((r) => (
              <li key={r.id} className="py-2.5 text-sm">
                <div className="flex items-center justify-between"><Link href={`/portal/requests/${r.id}`} className="font-medium hover:text-accent">{r.reference} · {r.service_name}</Link><StatusBadge status={r.status} /></div>
                <div className="text-xs text-muted-foreground">{r.parent_name} · {fmtDate(r.requested_start)}</div>
              </li>
            ))}</ul>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
