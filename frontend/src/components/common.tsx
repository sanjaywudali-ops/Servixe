"use client";
import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

export const EMERGENCY_TEXT =
  "Servixe is a non-emergency coordination service. In an emergency, contact your local emergency services immediately (India: 112).";

export function EmergencyBanner({ className }: { className?: string }) {
  return (
    <div className={cn("bg-primary text-primary-foreground text-xs sm:text-sm", className)}>
      <div className="container py-2 text-center">{EMERGENCY_TEXT}</div>
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function State({ loading, error, empty, emptyText = "Nothing here yet." }: { loading?: boolean; error?: string | null; empty?: boolean; emptyText?: string }) {
  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>;
  if (error) return <Alert tone="error">{error}</Alert>;
  if (empty) return <p className="rounded-lg border border-dashed py-10 text-center text-sm text-muted-foreground">{emptyText}</p>;
  return null;
}

export function Stat({ label, value, href, tone }: { label: string; value: React.ReactNode; href?: string; tone?: "warn" | "bad" }) {
  const inner = (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={cn("mt-1 text-2xl font-bold", tone === "warn" && "text-warning", tone === "bad" && "text-destructive")}>{value}</div>
    </div>
  );
  return href ? <Link href={href} className="block hover:opacity-90">{inner}</Link> : inner;
}

export function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1.5 text-sm">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="col-span-2 break-words">{v ?? "—"}</dd>
    </div>
  );
}

export function Timeline({ events }: { events: { id: string; event_type: string; to_status?: string | null; message?: string | null; created_at: string }[] }) {
  if (!events.length) return <p className="text-sm text-muted-foreground">No updates yet.</p>;
  return (
    <ol className="relative ml-2 space-y-4 border-l pl-5">
      {events.map((e) => (
        <li key={e.id} className="relative">
          <span className="absolute -left-[27px] top-1.5 h-2.5 w-2.5 rounded-full bg-accent" />
          <div className="text-xs text-muted-foreground">{new Date(e.created_at).toLocaleString("en-IN")}</div>
          <div className="text-sm">
            {e.to_status && <strong className="mr-1 capitalize">{e.to_status.replace(/_/g, " ")}</strong>}
            {e.message}
          </div>
        </li>
      ))}
    </ol>
  );
}
