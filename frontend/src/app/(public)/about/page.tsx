import type { Metadata } from "next";

export const metadata: Metadata = { title: "About Servixe" };

export default function About() {
  return (
    <div className="container max-w-3xl space-y-6 py-12">
      <h1 className="text-3xl font-bold">About Servixe</h1>
      <p className="text-muted-foreground">
        Servixe exists for families who live far from their parents. Our mission is simple: make it easy to arrange reliable, respectful, everyday support at home — and to know it was done.
      </p>
      <section><h2 className="text-xl font-semibold">Operating approach</h2><p className="mt-1 text-sm text-muted-foreground">We are a coordinator. Every request is recorded in one system with consent, approval, assignment and completion evidence, so nothing depends on scattered chats or memory.</p></section>
      <section><h2 className="text-xl font-semibold">How we verify providers</h2><p className="mt-1 text-sm text-muted-foreground">Identity, address, references and appropriate licence/registration/insurance checks; police verification where appropriate and lawful; in-person interviews; scenario checks, induction and supervised trial jobs for anyone entering a home. We keep a primary and backup provider per service and micro-area where feasible.</p></section>
      <section><h2 className="text-xl font-semibold">Service limitations</h2><ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground"><li>We do not provide regulated clinical care, make medical decisions, or interpret medical reports.</li><li>We are not an emergency-response service.</li><li>We do not take custody of cash, or collect PINs, OTPs, passwords, card security codes or banking credentials.</li><li>We do not act as a legal or financial representative.</li></ul></section>
    </div>
  );
}
