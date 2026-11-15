"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { PageHeader, State } from "@/components/common";
import { useFetch } from "@/lib/hooks";
import type { Parent } from "@/lib/types";

export default function Parents() {
  const { data, loading, error } = useFetch<Parent[]>("/portal/parents");
  return (
    <>
      <PageHeader title="My parents" description="Parent profiles and the permissions you hold for each." actions={<Button asChild variant="accent"><Link href="/portal/parents/new">Add parent</Link></Button>} />
      <State loading={loading} error={error} empty={data?.length === 0} />
      <div className="grid gap-4 md:grid-cols-2">
        {data?.map((p) => (
          <Card key={p.id}>
            <CardHeader><CardTitle><Link href={`/portal/parents/${p.id}`} className="hover:text-accent">{p.full_name}</Link></CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <div>{[p.area, p.city].filter(Boolean).join(", ")}</div>
              <div className="flex items-center gap-2">Authorisation <StatusBadge status={p.authorisation?.status} /> Consent <StatusBadge status={p.consent_status} /></div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
