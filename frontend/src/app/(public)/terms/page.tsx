import type { Metadata } from "next";
import { Alert } from "@/components/ui/alert";
import { EMERGENCY_TEXT } from "@/components/common";

export const metadata: Metadata = { title: "Terms, cancellation & refunds" };

export default function Terms() {
  return (
    <div className="container max-w-3xl space-y-5 py-12">
      <h1 className="text-3xl font-bold">Terms, cancellation &amp; refunds</h1>
      <Alert tone="warning">Placeholder text. These terms must be drafted or reviewed by qualified legal, tax and consumer-protection advisers before launch.</Alert>
      <Alert tone="error"><strong>Not for emergencies.</strong> {EMERGENCY_TEXT}</Alert>
      {[
        ["Our role", "Servixe coordinates non-clinical parent-support services through independent verified local partners. We do not provide regulated clinical care, make medical decisions, interpret medical reports, or guarantee emergency response."],
        ["Consent and authority", "Services for a parent proceed only after the parent’s informed agreement is recorded. The person paying is not automatically authorised to make decisions about a parent’s home, information or photographs."],
        ["Quotes and approval", "No paid third-party work begins until you approve the quoted scope and amount. If provider cost, scope or timing changes materially, work pauses until you approve again."],
        ["Cancellation and refunds", "Cancellation windows, fees and refund rules will be shown here and on each quote."],
        ["Payments", "Payments are made through a hosted checkout. We never store card security codes, PINs, OTPs or banking credentials, and we do not hold cash on your behalf."],
      ].map(([t, d]) => (<section key={t}><h2 className="text-xl font-semibold">{t}</h2><p className="mt-1 text-sm text-muted-foreground">{d}</p></section>))}
    </div>
  );
}
