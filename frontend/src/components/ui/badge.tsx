import { cn } from "@/lib/utils";
import { label } from "@/lib/utils";

const tones: Record<string, string> = {
  neutral: "bg-muted text-muted-foreground",
  info: "bg-secondary text-secondary-foreground",
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-destructive/15 text-destructive",
};

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: keyof typeof tones; className?: string }) {
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap", tones[tone], className)}>{children}</span>;
}

const STATUS_TONE: Record<string, keyof typeof tones> = {
  new_request: "info", under_review: "info", quote_pending: "warning", approval_pending: "warning", assigned: "info",
  in_progress: "info", quality_check: "warning", completed: "success", closed: "neutral", cancelled: "neutral", rejected: "danger",
  rescheduled: "warning", no_show: "danger", failed: "danger", refund_pending: "warning", incident_open: "danger",
  pending: "warning", approved: "success", superseded: "neutral", expired: "neutral", offered: "warning", accepted: "success",
  paid: "success", issued: "warning", draft: "neutral", void: "neutral", refunded: "neutral", active: "success", revoked: "neutral",
  verified: "success", applicant: "neutral", in_verification: "warning", suspended: "danger",
  open: "danger", investigating: "warning", resolved: "success", low: "neutral", medium: "warning", high: "danger", critical: "danger",
  new: "info", contacted: "warning", converted: "success", sent: "info", delivered: "success", failed_: "danger", queued: "warning",
};

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{label(status)}</Badge>;
}
