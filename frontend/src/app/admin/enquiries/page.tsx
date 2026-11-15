"use client";
import { Select } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { patch } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { fmtDate, label } from "@/lib/utils";

interface Enq { id: string; name: string; country: string; contact_method: string; contact_value: string; parent_city_area: string; service_interest: string; callback_requested: boolean; status: string; handled_by: string | null; created_at: string }

export default function Enquiries() {
  const { data, loading, error, reload } = useFetch<Enq[]>("/admin/enquiries");
  return (
    <>
      <PageHeader title="Enquiries" description="Lead-stage details only. Convert good leads by inviting them to register." />
      <State loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && <Table><THead><tr><TH>Received</TH><TH>Name</TH><TH>Country</TH><TH>Contact</TH><TH>Parent area</TH><TH>Interest</TH><TH>Status</TH></tr></THead><tbody>
        {data.map((e) => <TR key={e.id}><TD>{fmtDate(e.created_at)}</TD><TD>{e.name}{e.callback_requested && <span className="ml-1 text-xs text-accent">(callback)</span>}</TD><TD>{e.country}</TD><TD>{label(e.contact_method)}: {e.contact_value}</TD><TD>{e.parent_city_area}</TD><TD>{e.service_interest}</TD>
          <TD><Select className="min-h-8 py-1" value={e.status} onChange={async (ev) => { await patch(`/admin/enquiries/${e.id}`, { status: ev.target.value }); reload(); }}>{["new", "contacted", "converted", "closed"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
