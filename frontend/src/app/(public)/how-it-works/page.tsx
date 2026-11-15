import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "How it works" };

const steps = [
  ["Enquiry", "Tell us your name, country, how to reach you, your parent’s city/area and the service you’re interested in. We call you back."],
  ["Create your account & add your parent", "Register, then add your parent’s profile. You do not automatically gain authority over your parent’s home, information or photographs."],
  ["Parent consent", "Our team records your parent’s informed agreement for the relevant activities (visits, errands, photographs, updates, sharing information) and activates your permissions."],
  ["Request", "Describe the task, timing, location and any budget cap."],
  ["Quote & approval", "We confirm provider or third-party costs and send you a quote. You approve or decline. Changes to price or scope need renewed approval."],
  ["Provider assignment", "A verified provider is assigned (with a backup where feasible) and receives only the minimum information needed."],
  ["Completion & update", "The provider checks in, completes a checklist and — only where your parent has agreed — shares photos. We review quality and send you an update."],
  ["Invoice & close-out", "You receive an invoice. The request is closed after quality and payment checks."],
];

export default function HowItWorks() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-bold">How it works</h1>
      <ol className="mt-8 space-y-5">
        {steps.map(([t, d], i) => (
          <li key={t} className="flex gap-4">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent font-bold text-accent-foreground">{i + 1}</span>
            <div><h2 className="text-lg font-semibold">{t}</h2><p className="text-sm text-muted-foreground">{d}</p></div>
          </li>
        ))}
      </ol>
      <Button asChild variant="accent" className="mt-8"><Link href="/contact">Request a callback</Link></Button>
    </div>
  );
}
