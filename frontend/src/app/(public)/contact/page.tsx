"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/form";
import { Alert } from "@/components/ui/alert";
import { post } from "@/lib/api";
import { useAction } from "@/lib/hooks";

export default function Contact() {
  const [form, setForm] = useState({ name: "", country: "", contact_method: "email", contact_value: "", parent_city_area: "", service_interest: "", callback_requested: true, consent_to_contact: false });
  const [done, setDone] = useState<string | null>(null);
  const { busy, error, run } = useAction();
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const r = await run(() => post<{ message: string }>("/public/enquiries", form));
    if (r) setDone(r.message);
  }

  return (
    <div className="container grid max-w-5xl gap-10 py-12 md:grid-cols-5">
      <div className="md:col-span-2">
        <h1 className="text-3xl font-bold">Contact &amp; enquiry</h1>
        <p className="mt-3 text-sm text-muted-foreground">Share a few basic details and our team will call or message you back. Pilot area: Nellore, Andhra Pradesh.</p>
        <Alert tone="warning" className="mt-5"><strong>Please don’t include medical details</strong> or health records in this form. We’ll discuss your parent’s needs with you directly.</Alert>
        <Alert tone="error" className="mt-3"><strong>Not for emergencies.</strong> In an emergency contact local emergency services (India: 112).</Alert>
      </div>
      <div className="md:col-span-3">
        {done ? <Alert tone="success">{done}</Alert> : (
          <form onSubmit={submit} className="grid gap-4 rounded-lg border bg-card p-5">
            <Field label="Your name"><Input required minLength={2} value={form.name} onChange={(e) => set("name", e.target.value)} autoComplete="name" /></Field>
            <Field label="Country you live in"><Input required value={form.country} onChange={(e) => set("country", e.target.value)} autoComplete="country-name" /></Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Preferred contact method">
                <Select value={form.contact_method} onChange={(e) => set("contact_method", e.target.value)}>
                  <option value="email">Email</option><option value="phone">Phone call</option><option value="whatsapp">WhatsApp</option>
                </Select>
              </Field>
              <Field label={form.contact_method === "email" ? "Email address" : "Phone number (with country code)"}>
                <Input required type={form.contact_method === "email" ? "email" : "tel"} value={form.contact_value} onChange={(e) => set("contact_value", e.target.value)} />
              </Field>
            </div>
            <Field label="Parent’s city / area" hint="e.g. Nellore – Stonehousepet"><Input required value={form.parent_city_area} onChange={(e) => set("parent_city_area", e.target.value)} /></Field>
            <Field label="Service you’re interested in"><Input required placeholder="e.g. weekly wellbeing visit, pharmacy pickup" value={form.service_interest} onChange={(e) => set("service_interest", e.target.value)} /></Field>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={form.callback_requested} onChange={(e) => set("callback_requested", e.target.checked)} /> Please call me back</label>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" required className="mt-1" checked={form.consent_to_contact} onChange={(e) => set("consent_to_contact", e.target.checked)} /> I agree to Servixe contacting me about this enquiry. See the <a href="/privacy" className="text-accent underline">privacy notice</a>.</label>
            {error && <Alert tone="error">{error}</Alert>}
            <Button type="submit" variant="accent" disabled={busy}>{busy ? "Sending…" : "Send enquiry"}</Button>
          </form>
        )}
      </div>
    </div>
  );
}
