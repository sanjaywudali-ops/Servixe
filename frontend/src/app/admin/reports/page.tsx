"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/form";
import { KV, PageHeader, Stat, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import { fmtDate, label, money } from "@/lib/utils";

interface Rep {
  period_days: number;
  requests: { created: number; completed: number; cancelled: number; avg_completion_hours: number | null };
  providers: { acceptance_rate: number; rejection_rate: number; no_shows: number };
  incidents: Record<string, number>;
  finance_minor: Record<string, number>;
  repeat_customers: number;
  provider_document_gaps: { provider_id: string; doc_type: string; expires_at: string }[];
}

export default function Reports() {
  const [days, setDays] = useState("30");
  const { data, loading, error } = useFetch<Rep>(`/admin/reports?days=${days}`);
  return (
    <>
      <PageHeader title="Reports" actions={<Select className="w-40" value={days} onChange={(e) => setDays(e.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="365">Last 12 months</option></Select>} />
      {!data ? <State loading={loading} error={error} /> : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Requests created" value={data.requests.created} /><Stat label="Completed" value={data.requests.completed} />
            <Stat label="Avg completion (hrs)" value={data.requests.avg_completion_hours ?? "—"} /><Stat label="Repeat customers" value={data.repeat_customers} />
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            <Card><CardHeader><CardTitle>Finance (INR view)</CardTitle></CardHeader><CardContent><dl>
              {Object.entries(data.finance_minor).map(([k, v]) => <KV key={k} k={label(k)} v={<span className={k === "contribution_margin" ? "font-bold" : ""}>{money(v)}</span>} />)}
            </dl><p className="mt-2 text-xs text-muted-foreground">Contribution margin = coordination fees collected less refunds. Provider charges are pass-through. Multi-currency reconciliation is manual in the pilot.</p></CardContent></Card>
            <Card><CardHeader><CardTitle>Provider performance</CardTitle></CardHeader><CardContent><dl>
              <KV k="Acceptance rate" v={`${Math.round(data.providers.acceptance_rate * 100)}%`} /><KV k="Rejection rate" v={`${Math.round(data.providers.rejection_rate * 100)}%`} /><KV k="No-shows" v={data.providers.no_shows} /><KV k="Cancelled requests" v={data.requests.cancelled} />
            </dl></CardContent></Card>
            <Card><CardHeader><CardTitle>Incidents by severity</CardTitle></CardHeader><CardContent><dl>{Object.entries(data.incidents).map(([k, v]) => <KV key={k} k={label(k)} v={v} />)}</dl></CardContent></Card>
          </div>
          <Card><CardHeader><CardTitle>Provider document expiry &amp; verification gaps (30 days)</CardTitle></CardHeader><CardContent>
            {data.provider_document_gaps.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : <ul className="text-sm">{data.provider_document_gaps.map((g, i) => <li key={i} className="py-1">{label(g.doc_type)} — expires {fmtDate(g.expires_at, false)} (provider {g.provider_id.slice(0, 8)})</li>)}</ul>}
          </CardContent></Card>
        </div>
      )}
    </>
  );
}
