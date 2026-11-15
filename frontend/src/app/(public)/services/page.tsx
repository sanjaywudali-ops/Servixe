import type { Metadata } from "next";
import Link from "next/link";
import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { loadServices } from "@/lib/public-data";

export const metadata: Metadata = { title: "Services" };
export const dynamic = "force-dynamic";

export default async function ServicesPage() {
  const services = await loadServices();
  return (
    <div className="container py-12">
      <h1 className="text-3xl font-bold">Services</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">Plain-language descriptions of what is — and isn’t — included. All services are non-clinical and delivered by verified local partners.</p>
      <div className="mt-8 grid gap-5 md:grid-cols-2">
        {services.map((s) => (
          <Card key={s.id}>
            <CardHeader><CardTitle className="text-lg">{s.name}</CardTitle><CardDescription>{s.description || s.summary}</CardDescription></CardHeader>
            <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
              <div><h3 className="mb-1.5 text-sm font-semibold">Included</h3><ul className="space-y-1">{s.inclusions.map((i) => <li key={i} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />{i}</li>)}</ul></div>
              <div><h3 className="mb-1.5 text-sm font-semibold">Not included</h3><ul className="space-y-1">{s.exclusions.map((i) => <li key={i} className="flex gap-2"><X className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden />{i}</li>)}</ul></div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="mt-8"><Button asChild variant="accent"><Link href="/contact">Ask about a service</Link></Button></div>
    </div>
  );
}
