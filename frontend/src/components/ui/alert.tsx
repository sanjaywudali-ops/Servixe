import { cn } from "@/lib/utils";

export function Alert({ tone = "info", children, className }: { tone?: "info" | "error" | "success" | "warning"; children: React.ReactNode; className?: string }) {
  const t = {
    info: "border-accent/40 bg-secondary text-secondary-foreground",
    error: "border-destructive/40 bg-destructive/10 text-destructive",
    success: "border-success/40 bg-success/10 text-success",
    warning: "border-warning/40 bg-warning/10 text-warning",
  }[tone];
  return <div role={tone === "error" ? "alert" : "status"} className={cn("rounded-md border px-4 py-3 text-sm", t, className)}>{children}</div>;
}
