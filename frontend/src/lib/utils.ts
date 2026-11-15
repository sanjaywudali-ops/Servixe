import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

export function money(minor: number | null | undefined, currency = "INR"): string {
  if (minor == null) return "—";
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency }).format(minor / 100);
}

export function toMinor(major: string | number): number {
  return Math.round(Number(major || 0) * 100);
}

export function fmtDate(iso?: string | null, withTime = true): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export const label = (s?: string | null) => (s ? s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—");

/** datetime-local input value -> ISO string (or undefined) */
export const localToIso = (v: string) => (v ? new Date(v).toISOString() : undefined);
