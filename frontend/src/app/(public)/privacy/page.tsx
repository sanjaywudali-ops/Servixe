import type { Metadata } from "next";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = { title: "Privacy notice" };

export default function Privacy() {
  return (
    <div className="container max-w-3xl space-y-5 py-12">
      <h1 className="text-3xl font-bold">Privacy notice</h1>
      <Alert tone="warning">Placeholder text. This notice must be reviewed and finalised by a qualified Indian privacy/legal adviser before accepting live customers.</Alert>
      {[
        ["What we collect", "Enquiry stage: name, country, contact method and details, your parent’s city/area and service interest. Account stage: profile, parent profile, consent records, requests, quotes, invoices and service updates. Providers: verification documents and job records. We do not ask for health records in the enquiry form."],
        ["Why we collect it", "To coordinate the services you request, obtain your parent’s consent, keep records of approvals and completion, issue invoices and keep everyone safe."],
        ["Who can see it", "Each role sees only what it needs. Providers see only details for jobs assigned to them, and address/contact details only after accepting a job. Staff access to sensitive records is logged."],
        ["Photographs and updates", "Photographs are taken only where your parent has agreed, and are shared with you only when released by our operations team."],
        ["Retention and deletion", "Retention periods for enquiries, profiles, provider documents, evidence, invoices and incident records will be published here once confirmed."],
        ["Your choices", "You can ask us to correct or delete your information, and your parent can withdraw consent. Contact us using the details on the Contact page."],
      ].map(([t, d]) => (<section key={t}><h2 className="text-xl font-semibold">{t}</h2><p className="mt-1 text-sm text-muted-foreground">{d}</p></section>))}
    </div>
  );
}
