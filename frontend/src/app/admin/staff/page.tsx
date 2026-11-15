"use client";
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { patch, post } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate } from "@/lib/utils";

interface U { id: string; email: string; full_name: string; role: string; is_active: boolean; mfa_enabled: boolean; last_login_at: string | null }

export default function Staff() {
  const { data, loading, error, reload } = useFetch<U[]>("/admin/staff");
  const [f, setF] = useState({ email: "", full_name: "", role: "support" });
  const a = useAction();
  return (
    <>
      <PageHeader title="Staff" description="Staff are invited by email, set their own password and must enrol in MFA at first sign-in." />
      <Card className="mb-5"><CardContent className="grid gap-3 pt-5 sm:grid-cols-4">
        <Field label="Full name"><Input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
        <Field label="Email"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Role"><Select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="support">Support / coordinator</option><option value="admin">Admin</option></Select></Field>
        <div className="flex items-end"><Button disabled={a.busy || !f.email || !f.full_name} onClick={() => a.run(async () => { await post("/admin/staff", f); setF({ email: "", full_name: "", role: "support" }); reload(); })}>Invite</Button></div>
        {a.error && <Alert tone="error" className="sm:col-span-4">{a.error}</Alert>}
      </CardContent></Card>
      <State loading={loading} error={error} />
      {data && <Table><THead><tr><TH>Name</TH><TH>Email</TH><TH>Role</TH><TH>MFA</TH><TH>Last sign-in</TH><TH>Status</TH><TH></TH></tr></THead><tbody>
        {data.map((u) => <TR key={u.id}><TD>{u.full_name}</TD><TD>{u.email}</TD><TD>{u.role}</TD><TD>{u.mfa_enabled ? "Enabled" : "Not yet"}</TD><TD>{fmtDate(u.last_login_at)}</TD><TD><StatusBadge status={u.is_active ? "active" : "revoked"} /></TD>
          <TD><Button size="sm" variant="outline" onClick={() => a.run(async () => { await patch(`/admin/staff/${u.id}`, { is_active: !u.is_active }); reload(); })}>{u.is_active ? "Deactivate" : "Reactivate"}</Button></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
