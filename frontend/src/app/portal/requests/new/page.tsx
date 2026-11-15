"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { PageHeader, State } from "@/components/common";
import { post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import type { Parent, RequestSummary, Service } from "@/lib/types";
import { localToIso, toMinor } from "@/lib/utils";

export default function NewRequest() {
  const router = useRouter();
  const parents = useFetch<Parent[]>("/portal/parents");
  const services = useFetch<Service[]>("/public/services");
  const [f, setF] = useState({ parent_id: "", service_id: "", task_details: "", requested_start: "", requested_end: "", location_text: "", priority: "normal", budget: "" });
  const { busy, error, run } = useAction();
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const parent = parents.data?.find((p) => p.id === f.parent_id);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const r = await run(() => post<RequestSummary>("/portal/requests", {
      parent_id: f.parent_id, service_id: f.service_id, task_details: f.task_details, priority: f.priority,
      requested_start: localToIso(f.requested_start), requested_end: localToIso(f.requested_end),
      location_text: f.location_text || undefined, budget_cap_minor: f.budget ? toMinor(f.budget) : undefined,
    }));
    if (r) router.push(`/portal/requests/${r.id}`);
  }

  if (parents.data && parents.data.length === 0) return <Alert tone="warning">Please <Link className="underline" href="/portal/parents/new">add a parent</Link> first.</Alert>;
  return (
    <>
      <PageHeader title="New service request" description="We’ll review your request, confirm your parent’s consent and send you a quote to approve. No paid work starts before you approve." />
      <State loading={parents.loading} error={parents.error} />
      <form onSubmit={submit} className="grid max-w-2xl gap-4">
        <Field label="For which parent?"><Select required value={f.parent_id} onChange={(e) => set("parent_id", e.target.value)}><option value="">Select…</option>{parents.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</Select></Field>
        {parent && parent.authorisation?.status !== "active" && <Alert tone="warning">Your authorisation for {parent.full_name} is still pending. You can submit now; work begins after consent is recorded.</Alert>}
        <Field label="Service"><Select required value={f.service_id} onChange={(e) => set("service_id", e.target.value)}><option value="">Select…</option>{services.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></Field>
        <Field label="Task details" hint="Describe what you need. Please avoid medical details."><Textarea required minLength={5} maxLength={2000} value={f.task_details} onChange={(e) => set("task_details", e.target.value)} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Preferred start"><Input type="datetime-local" value={f.requested_start} onChange={(e) => set("requested_start", e.target.value)} /></Field>
          <Field label="Preferred end"><Input type="datetime-local" value={f.requested_end} onChange={(e) => set("requested_end", e.target.value)} /></Field>
        </div>
        <Field label="Location" hint="Leave blank to use your parent’s saved address."><Input value={f.location_text} onChange={(e) => set("location_text", e.target.value)} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Priority"><Select value={f.priority} onChange={(e) => set("priority", e.target.value)}><option value="normal">Normal</option><option value="urgent">Urgent (surcharge may apply)</option></Select></Field>
          <Field label="Budget limit (optional)" hint="Maximum you’re comfortable spending"><Input type="number" min="0" step="0.01" value={f.budget} onChange={(e) => set("budget", e.target.value)} /></Field>
        </div>
        {error && <Alert tone="error">{error}</Alert>}
        <Button type="submit" variant="accent" disabled={busy}>{busy ? "Submitting…" : "Submit request"}</Button>
      </form>
    </>
  );
}
