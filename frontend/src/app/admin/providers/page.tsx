"use client";
import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { Service } from "@/lib/types";

interface P { id: string; full_name: string; phone: string; email: string | null; status: string; capacity_per_week: number; provider_type: string }
interface Area { id: string; name: string }

export default function Providers() {
  const { data, loading, error, reload } = useFetch<P[]>("/admin/providers");
  const services = useFetch<Service[]>("/admin/catalogue/services");
  const areas = useFetch<Area[]>("/admin/catalogue/areas");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ full_name: "", phone: "", email: "", capacity_per_week: "10", send_invite: true });
  const [sids, setSids] = useState<string[]>([]);
  const [aids, setAids] = useState<string[]>([]);
  const a = useAction();
  const toggle = (arr: string[], set: (v: string[]) => void, id: string) => set(arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id]);

  return (
    <>
      <PageHeader title="Provider directory" actions={<Button variant="accent" onClick={() => setOpen(!open)}>{open ? "Close" : "Onboard provider"}</Button>} />
      {open && (
        <Card className="mb-5"><CardContent className="grid gap-3 pt-5 sm:grid-cols-2">
          <Field label="Full name"><Input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="Phone"><Input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></Field>
          <Field label="Email (needed for portal login)"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Capacity / week"><Input type="number" min="0" value={f.capacity_per_week} onChange={(e) => setF({ ...f, capacity_per_week: e.target.value })} /></Field>
          <div className="sm:col-span-2"><div className="mb-1 text-sm font-medium">Services covered</div><div className="flex flex-wrap gap-3 text-sm">{services.data?.map((s) => <label key={s.id} className="flex items-center gap-1.5"><input type="checkbox" checked={sids.includes(s.id)} onChange={() => toggle(sids, setSids, s.id)} />{s.name}</label>)}</div></div>
          <div className="sm:col-span-2"><div className="mb-1 text-sm font-medium">Service areas</div><div className="flex flex-wrap gap-3 text-sm">{areas.data?.map((s) => <label key={s.id} className="flex items-center gap-1.5"><input type="checkbox" checked={aids.includes(s.id)} onChange={() => toggle(aids, setAids, s.id)} />{s.name}</label>)}</div></div>
          <label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" checked={f.send_invite} onChange={(e) => setF({ ...f, send_invite: e.target.checked })} /> Send portal invite by email</label>
          {a.error && <Alert tone="error" className="sm:col-span-2">{a.error}</Alert>}
          <div><Button disabled={a.busy || !f.full_name || !f.phone} onClick={() => a.run(async () => { await post("/admin/providers", { full_name: f.full_name, phone: f.phone, email: f.email || null, capacity_per_week: Number(f.capacity_per_week), service_ids: sids, service_area_ids: aids, send_invite: f.send_invite && !!f.email }); setOpen(false); reload(); })}>Create provider</Button></div>
        </CardContent></Card>
      )}
      <State loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && <Table><THead><tr><TH>Name</TH><TH>Phone</TH><TH>Type</TH><TH>Capacity</TH><TH>Status</TH></tr></THead><tbody>
        {data.map((p) => <TR key={p.id}><TD><Link className="font-medium text-accent hover:underline" href={`/admin/providers/${p.id}`}>{p.full_name}</Link></TD><TD>{p.phone}</TD><TD>{p.provider_type}</TD><TD>{p.capacity_per_week}/wk</TD><TD><StatusBadge status={p.status} /></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
