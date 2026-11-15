"use client";
import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Select, Textarea } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate, label } from "@/lib/utils";

export interface Inc { id: string; reference: string; request_id: string | null; category: string; severity: string; status: string; description: string; event_time: string; owner_user_id: string | null; created_at: string }

export default function Incidents() {
  const { data, loading, error, reload } = useFetch<Inc[]>("/admin/incidents");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ category: "other", severity: "medium", description: "", request_id: "" });
  const a = useAction();
  return (
    <>
      <PageHeader title="Incident desk" description="Safety events and complaints. High/critical incidents on a request move it to Incident open." actions={<Button variant="outline" onClick={() => setOpen(!open)}>Log incident</Button>} />
      {open && <Card className="mb-5"><CardContent className="grid gap-3 pt-5 sm:grid-cols-2">
        <Field label="Category"><Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{["safety", "complaint", "missed_visit", "provider_misconduct", "other"].map((c) => <option key={c} value={c}>{label(c)}</option>)}</Select></Field>
        <Field label="Severity"><Select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })}>{["low", "medium", "high", "critical"].map((c) => <option key={c} value={c}>{label(c)}</option>)}</Select></Field>
        <Field label="Request ID (optional)" className="sm:col-span-2"><input className="min-h-10 rounded-md border border-input bg-card px-3 text-sm" value={f.request_id} onChange={(e) => setF({ ...f, request_id: e.target.value })} placeholder="UUID from the request URL" /></Field>
        <Field label="Description" className="sm:col-span-2"><Textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
        {a.error && <Alert tone="error" className="sm:col-span-2">{a.error}</Alert>}
        <div><Button disabled={a.busy || f.description.length < 5} onClick={() => a.run(async () => { await post("/admin/incidents", { category: f.category, severity: f.severity, description: f.description, request_id: f.request_id || null }); setOpen(false); setF({ category: "other", severity: "medium", description: "", request_id: "" }); reload(); })}>Save incident</Button></div>
      </CardContent></Card>}
      <State loading={loading} error={error} empty={data?.length === 0} emptyText="No incidents recorded." />
      {data && data.length > 0 && <Table><THead><tr><TH>Reference</TH><TH>Category</TH><TH>Severity</TH><TH>Status</TH><TH>Opened</TH><TH>Summary</TH></tr></THead><tbody>
        {data.map((i) => <TR key={i.id}><TD><Link className="font-medium text-accent hover:underline" href={`/admin/incidents/${i.id}`}>{i.reference}</Link></TD><TD>{label(i.category)}</TD><TD><StatusBadge status={i.severity} /></TD><TD><StatusBadge status={i.status} /></TD><TD>{fmtDate(i.created_at)}</TD><TD className="max-w-xs truncate">{i.description}</TD></TR>)}
      </tbody></Table>}
    </>
  );
}
