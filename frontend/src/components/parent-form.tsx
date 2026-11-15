"use client";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/form";
import { useAction } from "@/lib/hooks";
import type { Parent } from "@/lib/types";

export type ParentFormValue = Partial<Parent> & { relationship_to_parent?: string };

export function ParentForm({ initial, onSubmit, submitLabel, showRelationship }: { initial?: ParentFormValue; onSubmit: (v: Record<string, unknown>) => Promise<unknown>; submitLabel: string; showRelationship?: boolean }) {
  const [f, setF] = useState({
    full_name: initial?.full_name ?? "", phone: initial?.phone ?? "", preferred_language: initial?.preferred_language ?? "",
    address_line: initial?.address_line ?? "", city: initial?.city ?? "Nellore", area: initial?.area ?? "", location_notes: initial?.location_notes ?? "",
    emergency_contact_name: initial?.emergency_contact_name ?? "", emergency_contact_phone: initial?.emergency_contact_phone ?? "",
    contact_preferences: initial?.contact_preferences ?? "", relationship_to_parent: initial?.relationship_to_parent ?? "son/daughter",
  });
  const { busy, error, run } = useAction();
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const clean = () => Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));

  return (
    <form onSubmit={(e) => { e.preventDefault(); run(() => onSubmit({ ...clean(), full_name: f.full_name, city: f.city || "Nellore" })); }} className="grid max-w-2xl gap-4">
      <Alert>Keep sensitive information to the minimum necessary. Please don’t enter medical details here.</Alert>
      <Field label="Parent’s full name"><Input required minLength={2} value={f.full_name} onChange={(e) => set("full_name", e.target.value)} /></Field>
      {showRelationship && <Field label="Your relationship to them"><Input value={f.relationship_to_parent} onChange={(e) => set("relationship_to_parent", e.target.value)} /></Field>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Phone"><Input type="tel" value={f.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
        <Field label="Preferred language"><Input value={f.preferred_language} onChange={(e) => set("preferred_language", e.target.value)} /></Field>
      </div>
      <Field label="Address"><Input value={f.address_line} onChange={(e) => set("address_line", e.target.value)} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Area / locality"><Input value={f.area} onChange={(e) => set("area", e.target.value)} /></Field>
        <Field label="City"><Input value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
      </div>
      <Field label="Location notes" hint="Landmarks, gate access, etc."><Textarea value={f.location_notes} onChange={(e) => set("location_notes", e.target.value)} maxLength={500} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Emergency contact name (supplied by parent/family)"><Input value={f.emergency_contact_name} onChange={(e) => set("emergency_contact_name", e.target.value)} /></Field>
        <Field label="Emergency contact phone"><Input type="tel" value={f.emergency_contact_phone} onChange={(e) => set("emergency_contact_phone", e.target.value)} /></Field>
      </div>
      <Field label="Contact preferences"><Input value={f.contact_preferences} onChange={(e) => set("contact_preferences", e.target.value)} placeholder="e.g. calls after 10am, no calls during prayer time" /></Field>
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" variant="accent" disabled={busy}>{busy ? "Saving…" : submitLabel}</Button>
    </form>
  );
}
