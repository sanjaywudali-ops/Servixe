"use client";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { PageHeader, State } from "@/components/common";
import { del, post, put } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { Service } from "@/lib/types";
import { money, toMinor } from "@/lib/utils";

const SCOPES = ["home_visit", "errands", "photographs", "updates", "information_sharing"];
const blank = { code: "", name: "", summary: "", description: "", required_consent_scope: "home_visit", fee: "", urgent: "0", tax: "18" };
const slug = (n: string) => n.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40);
const svcBody = (s: Service, over: Partial<Service> = {}) => ({ code: s.code, name: s.name, summary: s.summary, description: s.description, inclusions: s.inclusions, exclusions: s.exclusions, requirements: s.requirements, required_consent_scope: s.required_consent_scope, is_active: s.is_active, sort_order: (s as Service & { sort_order?: number }).sort_order ?? 100, ...over });

interface Area { id: string; name: string; is_active: boolean }
interface Rule { id: string; service_id: string; service_area_id: string | null; coordination_fee_minor: number; urgent_surcharge_minor: number; tax_percent: number; currency: string }

export default function Catalogue() {
  const services = useFetch<Service[]>("/admin/catalogue/services");
  const areas = useFetch<Area[]>("/admin/catalogue/areas");
  const rules = useFetch<Rule[]>("/admin/catalogue/pricing");
  const a = useAction();
  const [area, setArea] = useState("");
  const [edit, setEdit] = useState<{ service_id: string; fee: string; urgent: string; tax: string } | null>(null);
  const [adding, setAdding] = useState(false);
  const [nu, setNu] = useState(blank);
  const [det, setDet] = useState<{ id: string; name: string; summary: string; description: string; scope: string } | null>(null);
  const reloadAll = () => { services.reload(); areas.reload(); rules.reload(); };
  const ruleFor = (sid: string) => rules.data?.find((r) => r.service_id === sid && !r.service_area_id);

  return (
    <>
      <PageHeader title="Catalogue & pricing" description="Services, service areas and coordination-fee rules. Quotes are calculated from these rules." actions={<Button variant="accent" onClick={() => setAdding(!adding)}>{adding ? "Cancel" : "Add service"}</Button>} />
      {a.error && <Alert tone="error" className="mb-4">{a.error}</Alert>}
      <State loading={services.loading} error={services.error} />
      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {adding && (
            <Card><CardHeader><CardTitle>New service</CardTitle></CardHeader><CardContent className="grid gap-3 text-sm">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name"><Input value={nu.name} onChange={(e) => setNu({ ...nu, name: e.target.value, code: slug(e.target.value) })} /></Field>
                <Field label="Code (auto)" hint="Lowercase letters, numbers, underscore. Cannot change later."><Input value={nu.code} onChange={(e) => setNu({ ...nu, code: e.target.value })} /></Field>
              </div>
              <Field label="Short summary"><Input maxLength={300} value={nu.summary} onChange={(e) => setNu({ ...nu, summary: e.target.value })} /></Field>
              <Field label="Description"><Textarea className="min-h-20" value={nu.description} onChange={(e) => setNu({ ...nu, description: e.target.value })} /></Field>
              <div className="grid gap-3 sm:grid-cols-4">
                <Field label="Consent needed"><Select value={nu.required_consent_scope} onChange={(e) => setNu({ ...nu, required_consent_scope: e.target.value })}>{SCOPES.map((x) => <option key={x} value={x}>{x}</option>)}</Select></Field>
                <Field label="Fee (INR)"><Input type="number" step="0.01" value={nu.fee} onChange={(e) => setNu({ ...nu, fee: e.target.value })} /></Field>
                <Field label="Urgent surcharge"><Input type="number" step="0.01" value={nu.urgent} onChange={(e) => setNu({ ...nu, urgent: e.target.value })} /></Field>
                <Field label="Tax %"><Input type="number" step="0.01" value={nu.tax} onChange={(e) => setNu({ ...nu, tax: e.target.value })} /></Field>
              </div>
              <div><Button disabled={a.busy || nu.name.length < 2 || nu.code.length < 2 || nu.fee === ""} onClick={() => a.run(async () => {
                const c = await post<Service>("/admin/catalogue/services", { code: nu.code, name: nu.name, summary: nu.summary, description: nu.description, required_consent_scope: nu.required_consent_scope, is_active: true, sort_order: 100 });
                await post("/admin/catalogue/pricing", { service_id: c.id, currency: "INR", coordination_fee_minor: toMinor(nu.fee), urgent_surcharge_minor: toMinor(nu.urgent), tax_percent: Number(nu.tax) });
                setNu(blank); setAdding(false); reloadAll();
              })}>Create service</Button></div>
            </CardContent></Card>
          )}
          {services.data?.map((s) => { const r = ruleFor(s.id); return (
            <Card key={s.id}><CardHeader className="flex-row items-start justify-between gap-3"><div><CardTitle>{s.name}</CardTitle><p className="text-sm text-muted-foreground">{s.summary}</p></div><Badge tone={s.is_active ? "success" : "neutral"}>{s.is_active ? "Active" : "On hold"}</Badge></CardHeader>
              <CardContent className="text-sm">
                <p>Requires consent: <strong>{s.required_consent_scope}</strong></p>
                <p className="mt-1">Coordination fee: <strong>{r ? money(r.coordination_fee_minor, r.currency) : "not set"}</strong>{r && <> · Urgent: {money(r.urgent_surcharge_minor, r.currency)} · Tax {r.tax_percent}%</>}</p>
                {edit?.service_id === s.id ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-4"><Field label="Fee (INR)"><Input type="number" step="0.01" value={edit.fee} onChange={(e) => setEdit({ ...edit, fee: e.target.value })} /></Field><Field label="Urgent surcharge"><Input type="number" step="0.01" value={edit.urgent} onChange={(e) => setEdit({ ...edit, urgent: e.target.value })} /></Field><Field label="Tax %"><Input type="number" step="0.01" value={edit.tax} onChange={(e) => setEdit({ ...edit, tax: e.target.value })} /></Field>
                    <div className="flex items-end gap-2"><Button size="sm" disabled={a.busy} onClick={() => a.run(async () => { await post("/admin/catalogue/pricing", { service_id: s.id, currency: "INR", coordination_fee_minor: toMinor(edit.fee), urgent_surcharge_minor: toMinor(edit.urgent), tax_percent: Number(edit.tax) }); setEdit(null); reloadAll(); })}>Save</Button><Button size="sm" variant="ghost" onClick={() => setEdit(null)}>Cancel</Button></div></div>
                ) : det?.id === s.id ? (
                  <div className="mt-3 grid gap-3">
                    <Field label="Name"><Input value={det.name} onChange={(e) => setDet({ ...det, name: e.target.value })} /></Field>
                    <Field label="Short summary"><Input maxLength={300} value={det.summary} onChange={(e) => setDet({ ...det, summary: e.target.value })} /></Field>
                    <Field label="Description"><Textarea className="min-h-20" value={det.description} onChange={(e) => setDet({ ...det, description: e.target.value })} /></Field>
                    <Field label="Consent needed"><Select value={det.scope} onChange={(e) => setDet({ ...det, scope: e.target.value })}>{SCOPES.map((x) => <option key={x} value={x}>{x}</option>)}</Select></Field>
                    <div className="flex gap-2"><Button size="sm" disabled={a.busy || det.name.length < 2} onClick={() => a.run(async () => { await put(`/admin/catalogue/services/${s.id}`, svcBody(s, { name: det.name, summary: det.summary, description: det.description, required_consent_scope: det.scope })); setDet(null); reloadAll(); })}>Save details</Button><Button size="sm" variant="ghost" onClick={() => setDet(null)}>Cancel</Button></div>
                  </div>
                ) : (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => setEdit({ service_id: s.id, fee: r ? String(r.coordination_fee_minor / 100) : "", urgent: r ? String(r.urgent_surcharge_minor / 100) : "0", tax: r ? String(r.tax_percent) : "18" })}>Edit pricing</Button>
                    <Button size="sm" variant="outline" onClick={() => setDet({ id: s.id, name: s.name, summary: s.summary, description: s.description, scope: s.required_consent_scope ?? "home_visit" })}>Edit details</Button>
                    <Button size="sm" variant="outline" disabled={a.busy} onClick={() => a.run(async () => { await put(`/admin/catalogue/services/${s.id}`, svcBody(s, { is_active: !s.is_active })); reloadAll(); })}>{s.is_active ? "Put on hold" : "Reactivate"}</Button>
                    <Button size="sm" variant="destructive" disabled={a.busy} onClick={() => { if (confirm(`Delete “${s.name}” permanently? Services that already have requests cannot be deleted — put them on hold instead.`)) a.run(async () => { await del(`/admin/catalogue/services/${s.id}`); reloadAll(); }); }}>Delete</Button>
                  </div>
                )}
              </CardContent></Card>); })}
        </div>
        <Card><CardHeader><CardTitle>Service areas</CardTitle></CardHeader><CardContent className="space-y-3">
          <ul className="text-sm">{areas.data?.map((x) => <li key={x.id} className="flex justify-between border-b py-1.5"><span>{x.name}</span><Badge tone={x.is_active ? "success" : "neutral"}>{x.is_active ? "Active" : "Off"}</Badge></li>)}</ul>
          <div className="flex gap-2"><Input placeholder="New micro-area" value={area} onChange={(e) => setArea(e.target.value)} /><Button disabled={!area || a.busy} onClick={() => a.run(async () => { await post("/admin/catalogue/areas", { name: area }); setArea(""); reloadAll(); })}>Add</Button></div>
          <p className="text-xs text-muted-foreground">Confirm exact Nellore micro-areas in the requirements workshop.</p>
        </CardContent></Card>
      </div>
    </>
  );
}
