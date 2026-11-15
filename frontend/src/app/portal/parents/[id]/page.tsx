"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { KV, PageHeader, State } from "@/components/common";
import { ParentForm } from "@/components/parent-form";
import { del, patch } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Parent } from "@/lib/types";
import { fmtDate, label } from "@/lib/utils";

export default function ParentPage() {
  const { id } = useParams<{ id: string }>();
  const { data: p, loading, error, reload } = useFetch<Parent>(`/portal/parents/${id}`);
  const [editing, setEditing] = useState(false);
  if (!p) return <State loading={loading} error={error} />;
  const a = p.authorisation;
  return (
    <>
      <PageHeader title={p.full_name} actions={<><Button variant="outline" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit profile"}</Button><Button asChild variant="accent"><Link href="/portal/requests/new">New request</Link></Button></>} />
      {editing ? (
        <ParentForm initial={p} submitLabel="Save changes" onSubmit={async (v) => { await patch(`/portal/parents/${id}`, v); setEditing(false); reload(); }} />
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card><CardHeader><CardTitle>Profile</CardTitle></CardHeader><CardContent><dl>
            <KV k="Phone" v={p.phone} /><KV k="Language" v={p.preferred_language} /><KV k="Address" v={[p.address_line, p.area, p.city].filter(Boolean).join(", ")} />
            <KV k="Location notes" v={p.location_notes} /><KV k="Emergency contact" v={p.emergency_contact_name ? `${p.emergency_contact_name} (${p.emergency_contact_phone ?? "—"})` : null} /><KV k="Contact preferences" v={p.contact_preferences} />
          </dl></CardContent></Card>
          <Card><CardHeader><CardTitle>Your authority &amp; consent</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
            <div className="flex items-center gap-2">Authorisation <StatusBadge status={a?.status} /></div>
            {a?.status === "pending" && <Alert tone="warning">Awaiting your parent’s informed agreement. We’ll contact them and activate your permissions.</Alert>}
            {a?.status === "active" && (
              <div className="flex flex-wrap gap-1.5">
                {a.can_request_services && <Badge tone="info">Request services</Badge>}{a.can_receive_updates && <Badge tone="info">Receive updates</Badge>}
                {a.can_approve_costs && <Badge tone="info">Approve costs</Badge>}{a.can_view_evidence && <Badge tone="info">View photos/evidence</Badge>}
              </div>
            )}
            <h3 className="pt-2 font-semibold">Consent records</h3>
            {p.consents?.length ? <ul className="space-y-2">{p.consents.map((c) => (
              <li key={c.id} className="rounded-md border p-2.5">
                <div className="flex flex-wrap gap-1">{c.scopes.map((s) => <Badge key={s}>{label(s)}</Badge>)}</div>
                <div className="mt-1 text-xs text-muted-foreground">Given by {c.given_by} · {label(c.captured_via)} · {fmtDate(c.captured_at, false)}{c.revoked_at ? ` · revoked ${fmtDate(c.revoked_at, false)}` : ""}</div>
              </li>))}</ul> : <p className="text-muted-foreground">None recorded yet.</p>}
            {a && a.status !== "revoked" && <Button variant="destructive" size="sm" onClick={async () => { if (confirm("Remove your authorisation for this parent?")) { await del(`/portal/parents/${id}/authorisation`); reload(); } }}>Remove my authorisation</Button>}
          </CardContent></Card>
        </div>
      )}
    </>
  );
}
