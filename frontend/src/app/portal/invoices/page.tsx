"use client";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/badge";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import type { Invoice } from "@/lib/types";
import { fmtDate, money } from "@/lib/utils";

export default function Invoices() {
  const { data, loading, error } = useFetch<Invoice[]>("/portal/invoices");
  return (
    <>
      <PageHeader title="Invoices & payments" />
      <State loading={loading} error={error} empty={data?.length === 0} emptyText="No invoices yet." />
      {data && data.length > 0 && <Table><THead><tr><TH>Invoice</TH><TH>Issued</TH><TH>Total</TH><TH>Status</TH></tr></THead><tbody>
        {data.map((i) => <TR key={i.id}><TD><Link href={`/portal/invoices/${i.id}`} className="font-medium text-accent hover:underline">{i.number}</Link></TD><TD>{fmtDate(i.issued_at, false)}</TD><TD>{money(i.total_minor, i.currency)}</TD><TD><StatusBadge status={i.status} /></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
