import type { Service } from "./types";

/** Fallback copy shown if the API is unreachable. Final services/exclusions are confirmed in the pre-development workshop. */
export const FALLBACK_SERVICES: Service[] = [
  { id: "1", code: "wellbeing_visit", name: "Parent wellbeing visit", summary: "A verified local visitor checks in on your parent and sends you an update.", description: "", inclusions: ["Friendly in-person check-in", "Checklist-based visit", "Update to the family"], exclusions: ["Medical advice", "Emergency response"], requirements: "" },
  { id: "2", code: "errands", name: "Errands & groceries", summary: "Groceries and household errands done at your approved budget.", description: "", inclusions: ["Shopping to an approved list", "Receipts shared"], exclusions: ["Holding cash or banking credentials"], requirements: "" },
  { id: "3", code: "pharmacy_pickup", name: "Pharmacy pickup & delivery", summary: "Collect and deliver medicines already prescribed by your parent's doctor.", description: "", inclusions: ["Collection from the named pharmacy", "Receipt shared"], exclusions: ["Recommending or substituting medicines"], requirements: "" },
  { id: "4", code: "appointment_accompaniment", name: "Appointment accompaniment", summary: "Accompany your parent to an appointment with arranged transport.", description: "", inclusions: ["Transport coordination", "Accompaniment to and from"], exclusions: ["Relaying medical decisions"], requirements: "" },
];

export async function loadServices(): Promise<Service[]> {
  const base = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const r = await fetch(`${base}/api/v1/public/services`, { cache: "no-store", signal: AbortSignal.timeout(2500) });
    if (!r.ok) throw new Error("bad");
    const data = (await r.json()) as Service[];
    return data.length ? data : FALLBACK_SERVICES;
  } catch {
    return FALLBACK_SERVICES;
  }
}

export interface Pkg { id: string; name: string; description: string; interval: string; indicative_price_minor?: number | null; currency: string; entitlements: string[] }
export async function loadPackages(): Promise<Pkg[]> {
  const base = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const r = await fetch(`${base}/api/v1/public/packages`, { cache: "no-store", signal: AbortSignal.timeout(2500) });
    return r.ok ? ((await r.json()) as Pkg[]) : [];
  } catch {
    return [];
  }
}
