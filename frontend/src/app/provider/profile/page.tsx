"use client";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { KV, PageHeader } from "@/components/common";
import { api } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";
import { fmtDate, label } from "@/lib/utils";

interface Me { full_name: string; phone: string; email: string | null; status: string }
interface Doc { id: string; doc_type: string; filename: string; expires_at: string | null; review_status: string }

export default function Profile() {
  const me = useFetch<Me>("/provider/me");
  const docs = useFetch<Doc[]>("/provider/documents");
  const a = useAction();
  const file = useRef<HTMLInputElement>(null);
  const [t, setT] = useState("identity");
  const [exp, setExp] = useState("");
  return (
    <>
      <PageHeader title="My profile" />
      {me.data && <Card className="mb-4"><CardContent className="pt-5"><dl><KV k="Name" v={me.data.full_name} /><KV k="Phone" v={me.data.phone} /><KV k="Email" v={me.data.email} /><KV k="Status" v={<StatusBadge status={me.data.status} />} /></dl></CardContent></Card>}
      <Card><CardHeader><CardTitle>Verification documents</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
        <ul className="divide-y">{docs.data?.map((d) => <li key={d.id} className="flex items-center justify-between py-2"><span>{label(d.doc_type)}{d.expires_at ? ` · exp ${fmtDate(d.expires_at, false)}` : ""}</span><StatusBadge status={d.review_status} /></li>)}</ul>
        {a.error && <Alert tone="error">{a.error}</Alert>}
        <form className="grid gap-3 border-t pt-3" onSubmit={(e) => { e.preventDefault(); const f = file.current?.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); fd.append("doc_type", t); if (exp) fd.append("expires_at", new Date(exp).toISOString()); a.run(async () => { await api("/provider/documents", { form: fd }); if (file.current) file.current.value = ""; docs.reload(); }); }}>
          <Field label="Document type"><Select value={t} onChange={(e) => setT(e.target.value)}>{["identity", "address", "reference", "licence", "insurance", "police_verification", "other"].map((x) => <option key={x} value={x}>{label(x)}</option>)}</Select></Field>
          <Field label="Expiry (if any)"><Input type="date" value={exp} onChange={(e) => setExp(e.target.value)} /></Field>
          <input ref={file} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required className="text-sm" />
          <Button type="submit" disabled={a.busy}>Upload</Button>
        </form>
      </CardContent></Card>
    </>
  );
}
