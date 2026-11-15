import * as React from "react";
import { cn } from "@/lib/utils";

export const Table = ({ className, ...p }: React.HTMLAttributes<HTMLTableElement>) => (
  <div className="w-full overflow-x-auto rounded-lg border bg-card"><table className={cn("w-full text-sm", className)} {...p} /></div>
);
export const THead = (p: React.HTMLAttributes<HTMLTableSectionElement>) => <thead className="bg-primary text-primary-foreground text-left" {...p} />;
export const TH = ({ className, ...p }: React.ThHTMLAttributes<HTMLTableCellElement>) => <th className={cn("px-3 py-2.5 font-semibold whitespace-nowrap", className)} {...p} />;
export const TR = ({ className, ...p }: React.HTMLAttributes<HTMLTableRowElement>) => <tr className={cn("border-t even:bg-muted/40", className)} {...p} />;
export const TD = ({ className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => <td className={cn("px-3 py-2.5 align-top", className)} {...p} />;
