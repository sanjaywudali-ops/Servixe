"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import type { RequestSummary } from "@/lib/types";
import { fmtDate } from "@/lib/utils";

export default function Requests() {
  const { data, loading, error } = useFetch<RequestSummary[]>("/portal/requests");
  return (
    <>
      <PageHeader title="Service requests" actions={<Button asChild variant="accent"><Link href="/portal/requests/new">New request</Link></Button>} />
      <State loading={loading} error={error} empty={data?.length === 0} emptyText="No requests yet." />
      {data && data.length > 0 && (
        <Table><THead><tr><TH>Reference</TH><TH>Service</TH><TH>Parent</TH><TH>When</TH><TH>Status</TH></tr></THead><tbody>
          {data.map((r) => (<TR key={r.id}><TD><Link className="font-medium text-accent hover:underline" href={`/portal/requests/${r.id}`}>{r.reference}</Link></TD><TD>{r.service_name}</TD><TD>{r.parent_name}</TD><TD>{fmtDate(r.requested_start)}</TD><TD><StatusBadge status={r.status} /></TD></TR>))}
        </tbody></Table>
      )}
    </>
  );
}
