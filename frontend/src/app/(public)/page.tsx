import Link from "next/link";
import { ShieldCheck, HeartHandshake, FileCheck2, MessageSquareText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatAssistant } from "@/components/chat-assistant";
import { loadServices } from "@/lib/public-data";

export const dynamic = "force-dynamic";

const trust = [
  { icon: ShieldCheck, title: "Verified local partners", body: "Identity, address, references and relevant licences are checked, and providers complete an induction before entering a home." },
  { icon: HeartHandshake, title: "Your parent agrees first", body: "We record your parent's informed agreement for visits, errands, photographs and updates before work begins." },
  { icon: FileCheck2, title: "You approve every cost", body: "No paid third-party work starts until you approve a clear quote. If scope or price changes, we ask again." },
  { icon: MessageSquareText, title: "Clear updates, one record", body: "Every request, approval and completion update is tracked in your portal — not scattered across chats." },
];

export default async function Home() {
  const services = await loadServices();
  return (
    <>
      <section className="bg-gradient-to-b from-secondary to-background">
        <div className="container grid gap-10 py-16 md:grid-cols-2 md:py-24">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-accent">Pilot: Nellore, Andhra Pradesh</p>
            <h1 className="text-4xl font-bold leading-tight md:text-5xl">Be there for your parents, even when you can’t be.</h1>
            <p className="mt-5 max-w-xl text-lg text-muted-foreground">
              Servixe helps families overseas arrange everyday, non-clinical support for parents in Nellore — visits, errands, pharmacy pickups and accompaniment —
              delivered by verified local partners, with your approval at every step.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button asChild size="lg" variant="accent"><Link href="/contact">Request a callback</Link></Button>
              <Button asChild size="lg" variant="outline"><Link href="/how-it-works">How it works</Link></Button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">Servixe is not an emergency service. In an emergency call your local emergency number (India: 112).</p>
          </div>
          <div className="rounded-2xl border bg-card p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">What a request looks like</h2>
            <ol className="space-y-3 text-sm">
              {["You send a request from the portal", "We confirm your parent’s consent and availability", "You receive a quote and approve it", "A verified provider is assigned", "You get a completion update and invoice"].map((s, i) => (
                <li key={s} className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-accent-foreground">{i + 1}</span><span>{s}</span></li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="container py-14">
        <h2 className="text-2xl font-bold">Trust and safety, built in</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {trust.map(({ icon: Icon, title, body }) => (
            <Card key={title}><CardHeader><Icon className="h-6 w-6 text-accent" aria-hidden /><CardTitle>{title}</CardTitle></CardHeader><CardContent><p className="text-sm text-muted-foreground">{body}</p></CardContent></Card>
          ))}
        </div>
      </section>

      <section className="container pb-6">
        <div className="flex items-end justify-between"><h2 className="text-2xl font-bold">Key services</h2><Link href="/services" className="text-sm text-accent hover:underline">All services →</Link></div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {services.slice(0, 4).map((s) => (
            <Card key={s.id}><CardHeader><CardTitle>{s.name}</CardTitle><CardDescription>{s.summary}</CardDescription></CardHeader></Card>
          ))}
        </div>
      </section>

      <section className="container py-10">
        <div className="rounded-2xl bg-primary px-6 py-10 text-center text-primary-foreground">
          <h2 className="text-2xl font-bold !text-primary-foreground">Talk to us about your parents’ needs</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm opacity-90">Share a few basic details and we’ll call you back. Please don’t include medical details in the enquiry form.</p>
          <Button asChild variant="accent" size="lg" className="mt-5"><Link href="/contact">Request a callback</Link></Button>
        </div>
      </section>
      <ChatAssistant services={services.map((s) => ({ name: s.name, summary: s.summary }))} />
    </>
  );
}
