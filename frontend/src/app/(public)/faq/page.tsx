import type { Metadata } from "next";

export const metadata: Metadata = { title: "FAQs" };

const faqs: [string, string][] = [
  ["Where do you operate?", "Our pilot covers selected areas of Nellore, Andhra Pradesh. Tell us your parent’s area when you enquire and we’ll confirm coverage."],
  ["How does payment work?", "You receive a quote and approve it before paid work begins. After completion you receive an invoice and pay through a secure hosted checkout. We never store card security codes or banking credentials."],
  ["Do my parents have to agree?", "Yes. We record your parent’s informed agreement for home visits, errands, photographs, updates and information sharing before work starts. Your parent can withdraw consent."],
  ["Can I cancel?", "You can cancel before a provider is assigned from your portal. Cancellation and refund terms are on the Terms page and are shown on each quote."],
  ["What are your response hours?", "Operating hours and response times for the pilot will be published here once confirmed. Requests submitted outside hours are handled the next working period."],
  ["What about emergencies?", "Servixe is not an emergency service. In an emergency, contact local emergency services immediately (India: 112)."],
  ["How is my family’s data handled?", "We collect only what is needed, restrict health-related information, keep documents in private storage, and record who accessed sensitive information. See the Privacy notice."],
];

export default function FAQ() {
  return (
    <div className="container max-w-3xl py-12">
      <h1 className="text-3xl font-bold">Frequently asked questions</h1>
      <div className="mt-6 divide-y rounded-lg border bg-card">
        {faqs.map(([q, a]) => (
          <details key={q} className="group p-4">
            <summary className="cursor-pointer list-none font-medium marker:hidden">{q}</summary>
            <p className="mt-2 text-sm text-muted-foreground">{a}</p>
          </details>
        ))}
      </div>
    </div>
  );
}
