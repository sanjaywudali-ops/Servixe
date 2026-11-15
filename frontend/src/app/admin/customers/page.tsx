"use client";
import Link from "next/link";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import { fmtDate } from "@/lib/utils";

interface C { id: string; full_name: string; email: string; country: string; phone: string | null; created_at: string }

export default function Customers() {
  const { data, loading, error } = useFetch<C[]>("/admin/customers");
  return (
    <>
      <PageHeader title="Customers & families" />
      <State loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && <Table><THead><tr><TH>Name</TH><TH>Email</TH><TH>Country</TH><TH>Joined</TH></tr></THead><tbody>
        {data.map((c) => <TR key={c.id}><TD><Link className="font-medium text-accent hover:underline" href={`/admin/customers/${c.id}`}>{c.full_name}</Link></TD><TD>{c.email}</TD><TD>{c.country}</TD><TD>{fmtDate(c.created_at, false)}</TD></TR>)}
      </tbody></Table>}
    </>
  );
}
