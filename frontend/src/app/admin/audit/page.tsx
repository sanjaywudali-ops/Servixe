"use client";
import { useState } from "react";
import { Input } from "@/components/ui/form";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import { fmtDate } from "@/lib/utils";

interface Row { id: string; created_at: string; actor_role: string | null; actor_user_id: string | null; action: string; entity_type: string; entity_id: string | null; before: unknown; after: unknown; ip: string | null }

export default function Audit() {
  const [action, setAction] = useState("");
  const { data, loading, error } = useFetch<Row[]>(`/admin/audit-logs${action ? `?action=${encodeURIComponent(action)}` : ""}`);
  return (
    <>
      <PageHeader title="Audit trail" description="Append-only record of administrative changes, consent changes, approvals, assignments, evidence access and financial actions." />
      <Input className="mb-4 w-64" placeholder="Filter by action prefix e.g. consent." value={action} onChange={(e) => setAction(e.target.value)} />
      <State loading={loading} error={error} empty={data?.length === 0} />
      {data && data.length > 0 && <Table><THead><tr><TH>When</TH><TH>Actor</TH><TH>Action</TH><TH>Entity</TH><TH>Details</TH></tr></THead><tbody>
        {data.map((r) => <TR key={r.id}><TD className="whitespace-nowrap">{fmtDate(r.created_at)}</TD><TD>{r.actor_role ?? "system"}<div className="text-xs text-muted-foreground">{r.actor_user_id?.slice(0, 8)}</div></TD><TD>{r.action}</TD><TD>{r.entity_type}<div className="text-xs text-muted-foreground">{r.entity_id?.slice(0, 8)}</div></TD><TD className="max-w-sm"><code className="block truncate text-xs" title={JSON.stringify({ before: r.before, after: r.after })}>{r.after ? JSON.stringify(r.after) : ""}</code></TD></TR>)}
      </tbody></Table>}
    </>
  );
}
