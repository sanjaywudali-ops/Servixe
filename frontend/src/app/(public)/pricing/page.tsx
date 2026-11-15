import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { loadPackages, loadServices } from "@/lib/public-data";
import { money } from "@/lib/utils";

export const metadata: Metadata = { title: "Packages & pricing" };
export const dynamic = "force-dynamic";

export default async function PricingPage() {
  const [services, packages] = await Promise.all([loadServices(), loadPackages()]);
  return (
    <div className="container py-12">
      <h1 className="text-3xl font-bold">Packages &amp; pricing</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Every job is priced as a clear quote: provider or third-party charges at cost, plus Servixe’s coordination fee and applicable taxes.
        Final quotes depend on location, timing and provider cost. You approve the quote before any paid work begins.
      </p>

      <h2 className="mt-10 text-xl font-semibold">Indicative per-job ranges</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {services.map((s) => (
          <Card key={s.id}>
            <CardHeader><CardTitle>{s.name}</CardTitle></CardHeader>
            <CardContent>
              {s.indicative_min_minor ? <p className="text-lg font-semibold">{money(s.indicative_min_minor, s.currency)} – {money(s.indicative_max_minor, s.currency)}</p> : <p className="text-sm text-muted-foreground">Quote on request</p>}
              <p className="mt-1 text-xs text-muted-foreground">Indicative only. Excludes taxes.</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {packages.length > 0 && (
        <>
          <h2 className="mt-10 text-xl font-semibold">Plans</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {packages.map((p) => (
              <Card key={p.id}>
                <CardHeader><CardTitle>{p.name}</CardTitle><CardDescription>{p.description}</CardDescription></CardHeader>
                <CardContent>
                  {p.indicative_price_minor ? <p className="text-lg font-semibold">from {money(p.indicative_price_minor, p.currency)} / {p.interval.replace("_", " ")}</p> : null}
                  <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">{p.entitlements.map((e) => <li key={e}>{e}</li>)}</ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
      <div className="mt-8"><Button asChild variant="accent"><Link href="/contact">Request a callback</Link></Button></div>
    </div>
  );
}
