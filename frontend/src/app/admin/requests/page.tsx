"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { Input, Select } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import type { RequestSummary } from "@/lib/types";
import { fmtDate, label } from "@/lib/utils";

const STATUSES = ["new_request", "under_review", "quote_pending", "approval_pending", "assigned", "in_progress", "quality_check", "completed", "closed", "cancelled", "rejected", "rescheduled", "no_show", "failed", "refund_pending", "incident_open"];

function List() {
  const sp = useSearchParams();
  const [status, setStatus] = useState(sp.get("status") ?? "");
  const [q, setQ] = useState("");
  const { data, loading, error } = useFetch<RequestSummary[]>(`/admin/requests?${new URLSearchParams({ ...(status && { status }), ...(q && { q }) })}`);
  return (
    <>
      <PageHeader title="Requests" />
      <div className="mb-4 flex flex-wrap gap-3">
        <Select className="w-52" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select>
        <Input className="w-52" placeholder="Search reference" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <State loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && <Table><THead><tr><TH>Reference</TH><TH>Service</TH><TH>Parent</TH><TH>Requested</TH><TH>Priority</TH><TH>Status</TH></tr></THead><tbody>
        {data.map((r) => <TR key={r.id}><TD><Link className="font-medium text-accent hover:underline" href={`/admin/requests/${r.id}`}>{r.reference}</Link></TD><TD>{r.service_name}</TD><TD>{r.parent_name}</TD><TD>{fmtDate(r.requested_start)}</TD><TD>{label(r.priority)}</TD><TD><StatusBadge status={r.status} /></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
export default function Page() { return <Suspense><List /></Suspense>; }
