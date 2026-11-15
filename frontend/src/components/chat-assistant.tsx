"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Menu, MessageCircle, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, post } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";

/**
 * Guided assistant for the public landing page. Deliberately NOT an open-ended AI:
 *  - answers come from fixed, reviewed copy plus the live service list passed in by the server page;
 *  - new-user details are collected step by step and sent to the existing /public/enquiries endpoint
 *    (the same lead-stage fields as the contact form – no health information is ever requested);
 *  - emergency / medical wording is detected and answered with the emergency notice instead of being processed.
 */

export interface ChatService { name: string; summary: string }
interface Msg { id: number; from: "bot" | "user"; text: string; at: string; links?: { href: string; label: string }[] }
type Step = "idle" | "name" | "country" | "method" | "value" | "area" | "service" | "confirm";
interface Lead { name: string; country: string; contact_method: "email" | "phone" | "whatsapp"; contact_value: string; parent_city_area: string; service_interest: string }

const EMERGENCY = "If this is an emergency, please contact your local emergency services right now (India: 112). Servixe is a non-emergency coordination service and cannot respond to emergencies or give medical advice.";
const EMERGENCY_RE = /\b(emergency|urgent medical|ambulance|heart attack|stroke|unconscious|collapsed|fell down|bleeding|can'?t breathe|not breathing|chest pain|suicid|dying|accident)\b/i;
const MEDICAL_RE = /\b(diagnos|symptom|prescri|dosage|dose|tablet|medicine for|treatment|disease|diabetes|bp|blood pressure|cancer|dementia|alzheimer|surgery|report shows)\b/i;

const TOPICS: { id: string; chip: string; re: RegExp }[] = [
  { id: "services", chip: "What services do you offer?", re: /service|offer|do you do|help with|errand|grocer|pharmacy|visit|accompan|appointment/i },
  { id: "how", chip: "How does it work?", re: /how|work|process|step|start|begin|get started/i },
  { id: "pricing", chip: "What does it cost?", re: /price|pricing|cost|fee|charge|how much|rate|pay|payment|invoice/i },
  { id: "safety", chip: "Is it safe? Who are the providers?", re: /safe|verified|trust|background|check|provider|partner|secure|privacy|data/i },
  { id: "area", chip: "Where do you operate?", re: /where|area|city|nellore|location|india|andhra|cover/i },
  { id: "consent", chip: "Does my parent have to agree?", re: /consent|agree|permission|authori[sz]|my parent.*(say|want|refuse)/i },
];

const ANSWERS: Record<string, { text: string; links?: { href: string; label: string }[] }> = {
  how: { text: "1) You send a request from your portal. 2) We confirm your parent's consent and availability. 3) You receive a clear quote and approve it. 4) A verified local provider is assigned. 5) You get a completion update and an invoice. No paid work starts until you approve the quote.", links: [{ href: "/how-it-works", label: "Full walkthrough" }] },
  pricing: { text: "You pay a coordination fee plus the actual cost of any third-party work (such as groceries or transport), passed through at cost. Every request gets a written quote first, and you approve it before anything starts. If the scope or price changes, we ask you again.", links: [{ href: "/pricing", label: "See pricing" }] },
  safety: { text: "Local partners are verified (identity, address, references, relevant licences) and complete an induction before visiting a home. Providers only see what they need for a job, and photographs are only taken if your parent has agreed. Every request and approval is recorded in your portal.", links: [{ href: "/about", label: "About Servixe" }] },
  area: { text: "We're piloting in Nellore, Andhra Pradesh, starting with a few neighbourhoods. Tell me your parent's area and our team will confirm whether we can serve it." },
  consent: { text: "Yes. Before any work begins we record your parent's informed agreement for visits, errands, photographs and updates. You, as the person paying, don't automatically get authority to request services; it's activated once your parent has agreed." },
};

let uid = 0;
const mk = (from: Msg["from"], text: string, links?: Msg["links"]): Msg => ({ id: ++uid, from, text, links, at: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) });

export function ChatAssistant({ services }: { services: ChatService[] }) {
  const { me } = useAuth();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [chips, setChips] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [lead, setLead] = useState<Partial<Lead>>({});
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const say = useCallback((text: string, links?: Msg["links"]) => setMsgs((m) => [...m, mk("bot", text, links)]), []);
  const menu = useCallback((signedIn: boolean) => setChips(signedIn
    ? ["What services do you offer?", "How does it work?", "What does it cost?", "Talk to a person"]
    : ["I'm new here", "I'm already a customer", ...TOPICS.slice(0, 3).map((t) => t.chip), "Talk to a person"]), []);

  const [welcomed, setWelcomed] = useState(false);
  const begin = () => {
    setWelcomed(true);
    if (me) {
      say(`Hello ${me.full_name?.split(" ")[0] || "there"}! I can answer quick questions, or you can head to your dashboard to manage requests.`, [{ href: homeFor(me.role), label: "Go to my dashboard" }]);
      menu(true);
    } else {
      say("I can answer quick questions about arranging support for your parents in Nellore. Are you new to Servixe, or already a customer?");
      menu(false);
    }
  };
  const showMenu = () => { if (!welcomed) return begin(); setStep("idle"); setLead({}); say("Sure, here's the main menu. What would you like to do?"); menu(signedIn); };

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" }); }, [msgs, chips]);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open, step]);
  useEffect(() => { const f = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false); window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f); }, []);

  const signedIn = !!me;
  const topic = (id: string) => {
    if (id === "services") {
      say(services.length ? "Here's what we currently offer:\n" + services.map((s) => `• ${s.name} – ${s.summary}`).join("\n") : "Please see our services page for the current list.", [{ href: "/services", label: "View all services" }]);
    } else if (ANSWERS[id]) say(ANSWERS[id].text, ANSWERS[id].links);
    setChips(signedIn ? ["What does it cost?", "How does it work?", "Talk to a person"] : ["Get started / request a callback", "What does it cost?", "How does it work?", "Is it safe? Who are the providers?"]);
  };

  const startLead = () => {
    setStep("name"); setLead({}); setChips(["Cancel"]);
    say("Happy to help. I'll ask a few quick questions so our team can call or message you. Please don't share any medical details here. First, what's your name?");
  };

  const cancelLead = () => { setStep("idle"); setLead({}); say("No problem, nothing was sent. What else can I help with?"); menu(signedIn); };

  const askService = (l: Partial<Lead>) => {
    setLead(l); setStep("service");
    say("Which service are you most interested in?");
    setChips([...services.slice(0, 4).map((s) => s.name), "Not sure yet", "Cancel"]);
  };

  const submitLead = async (l: Partial<Lead>) => {
    setBusy(true); setChips([]);
    try {
      await post("/public/enquiries", { ...l, callback_requested: true, consent_to_contact: true });
      say("Thank you. Your details have been sent and our team will contact you shortly. Servixe is not an emergency service. You can also create an account to arrange requests yourself.", [{ href: "/register", label: "Create an account" }]);
      setStep("idle"); setLead({}); menu(false);
    } catch (e) {
      say(e instanceof ApiError && e.status === 429 ? "You've sent several requests recently. Please try again in a few minutes, or use the contact form." : "Sorry, I couldn't send that just now. Please try again, or use the contact form.", [{ href: "/contact", label: "Contact form" }]);
      setStep("confirm"); setChips(["Yes, send it", "Cancel"]);
    } finally { setBusy(false); }
  };

  const handleLead = (text: string) => {
    const t = text.trim();
    if (/^cancel$/i.test(t)) return cancelLead();
    if (step === "name") {
      if (t.length < 2) return say("Could you give me your name (at least 2 characters)?");
      setLead({ ...lead, name: t.slice(0, 160) }); setStep("country");
      say(`Nice to meet you, ${t.split(" ")[0]}. Which country do you live in?`);
    } else if (step === "country") {
      if (t.length < 2) return say("Which country do you live in?");
      setLead({ ...lead, country: t.slice(0, 80) }); setStep("method");
      say("How would you like us to reach you?"); setChips(["Email", "Phone call", "WhatsApp", "Cancel"]);
    } else if (step === "method") {
      const m = /whats/i.test(t) ? "whatsapp" : /phone|call/i.test(t) ? "phone" : /mail/i.test(t) ? "email" : null;
      if (!m) return say("Please choose Email, Phone call or WhatsApp.");
      setLead({ ...lead, contact_method: m }); setStep("value");
      say(m === "email" ? "What's your email address?" : "What's your number, including the country code (e.g. +1 555 123 4567)?"); setChips(["Cancel"]);
    } else if (step === "value") {
      const m = lead.contact_method;
      if (m === "email" ? !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(t) : t.replace(/\D/g, "").length < 7) return say(m === "email" ? "That doesn't look like a valid email address. Could you check it?" : "That doesn't look like a valid number. Please include the country code.");
      setLead({ ...lead, contact_value: t.slice(0, 255) }); setStep("area");
      say("Which city or area in Nellore does your parent live in? (e.g. Stonehousepet)");
    } else if (step === "area") {
      if (t.length < 2) return say("Which city or area does your parent live in?");
      askService({ ...lead, parent_city_area: t.slice(0, 160) });
    } else if (step === "service") {
      askServiceDone(t);
    } else if (step === "confirm") {
      if (/^(yes|y|send|ok|sure)/i.test(t)) submitLead(lead);
      else say("Please choose \"Yes, send it\" or Cancel.");
    }
  };

  const askServiceDone = (t: string) => {
    const l = { ...lead, service_interest: (t || "Not sure yet").slice(0, 120) };
    setLead(l); setStep("confirm");
    say(`Please confirm: ${l.name} (${l.country}), contact by ${l.contact_method} at ${l.contact_value}; parent in ${l.parent_city_area}; interested in ${l.service_interest}.\n\nBy choosing "Yes, send it" you agree to Servixe contacting you about this enquiry (see the privacy notice).`, [{ href: "/privacy", label: "Privacy notice" }]);
    setChips(["Yes, send it", "Cancel"]);
  };

  const route = (raw: string) => {
    const t = raw.trim();
    if (!t) return;
    setMsgs((m) => [...m, mk("user", t)]);
    setInput("");
    if (step !== "idle") {
      // safety first, even mid-flow
      if (EMERGENCY_RE.test(t)) { say(EMERGENCY); return; }
      return handleLead(t);
    }
    if (EMERGENCY_RE.test(t)) return say(EMERGENCY);
    if (MEDICAL_RE.test(t)) {
      say("I can't give medical advice, and please don't share medical details here. Our team can discuss your parent's needs with you directly, and we can help with non-clinical support such as visits, errands and pharmacy pickups. Would you like a callback?");
      setChips(["Get started / request a callback", "What services do you offer?"]);
      return;
    }
    if (/new here|new to|^new$|first time/i.test(t)) { say("Welcome! The quickest way to start is to leave a few details so our team can contact you, or create an account to submit requests yourself."); setChips(["Get started / request a callback", "How does it work?", "What services do you offer?"]); setLead({}); return; }
    if (/already|existing|customer|my account|log ?in|sign ?in|password|invoice|my request/i.test(t)) {
      say(signedIn ? "You're signed in. Your dashboard has your parents, requests and invoices." : "Please sign in to see your requests and invoices. If you've forgotten your password you can reset it.", signedIn && me ? [{ href: homeFor(me.role), label: "Go to my dashboard" }] : [{ href: "/login", label: "Sign in" }, { href: "/forgot-password", label: "Reset password" }]);
      menu(signedIn); return;
    }
    if (/callback|call me|get started|sign ?up|register|enquir|talk to|speak|human|person|agent|contact/i.test(t)) {
      if (/talk to|speak|human|person|agent/i.test(t) && signedIn) { say("Our team is happy to help. You can raise a concern from any request in your portal, or send us an enquiry.", [{ href: "/contact", label: "Contact us" }]); menu(true); return; }
      return startLead();
    }
    const hit = TOPICS.find((x) => x.re.test(t));
    if (hit) return topic(hit.id);
    say("I'm not sure I understood that. I can tell you about our services, how it works, pricing and safety, or arrange a callback.");
    menu(signedIn);
  };

  const chip = (c: string) => {
    if (c === "Cancel") { setMsgs((m) => [...m, mk("user", c)]); return cancelLead(); }
    if (step !== "idle") { setMsgs((m) => [...m, mk("user", c)]); return handleLead(c); }
    route(c);
  };

  const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} aria-label="Open chat assistant" className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-accent px-4 py-3 text-sm font-semibold text-accent-foreground shadow-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-ring">
          <MessageCircle className="h-5 w-5" aria-hidden /> Chat with us
        </button>
      )}
      {open && (
        <div role="dialog" aria-label="Servixe assistant" className="fixed inset-x-3 bottom-3 z-50 flex h-[min(620px,85vh)] flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-[400px]">
          <div className="flex items-start justify-between border-b bg-card px-5 py-4">
            <div><div className="text-lg font-bold text-accent">Servixe</div><div className="text-sm text-accent/90">Trusted local support for your parents</div></div>
            <button onClick={() => setOpen(false)} aria-label="Close chat" className="rounded p-1 text-accent hover:bg-muted"><X className="h-6 w-6" /></button>
          </div>
          <div ref={logRef} role="log" aria-live="polite" className="flex-1 space-y-3 overflow-y-auto bg-muted/50 px-4 py-4 text-sm">
            <p className="text-center text-sm text-muted-foreground">{today}</p>

            <div className="w-[78%] overflow-hidden rounded-lg border bg-card shadow-sm">
              <svg viewBox="0 0 250 130" role="img" aria-label="A home with a heart, and a friendly greeting" className="block w-full">
                <defs><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#d9ecee" /><stop offset="1" stopColor="#e7ddf5" /></linearGradient></defs>
                <rect width="250" height="130" fill="url(#cg)" />
                <rect x="14" y="14" width="118" height="40" rx="12" fill="#fff" />
                <path d="M30 54 l-6 10 l16 -6 z" fill="#fff" />
                <text x="26" y="31" fontSize="9" fontWeight="700" fill="#1a3550">Hi! I'm here to help.</text>
                <text x="26" y="45" fontSize="8.5" fill="#475569">Let's get you started 😊</text>
                <path d="M32 112 v-26 l30 -24 l30 24 v26 z" fill="#fff" stroke="#1a3550" strokeWidth="2.5" strokeLinejoin="round" />
                <path d="M62 104 c-12 -8 -14 -12 -14 -17 a7 7 0 0 1 14 -3 a7 7 0 0 1 14 3 c0 5 -2 9 -14 17z" fill="#1a8a8f" />
                <circle cx="170" cy="86" r="12" fill="#f4c7a1" /><path d="M156 112 c0 -14 8 -20 14 -20 s14 6 14 20z" fill="#1a8a8f" />
                <circle cx="206" cy="92" r="10" fill="#f4c7a1" /><path d="M194 114 c0 -12 6 -17 12 -17 s12 5 12 17z" fill="#1a3550" />
                <path d="M184 96 q8 -8 12 0" stroke="#1a8a8f" strokeWidth="2" fill="none" strokeLinecap="round" />
              </svg>
              <p className="px-3 pt-3 text-sm">Hi there!!</p>
              <p className="px-3 pb-3 text-xs text-muted-foreground">I can share quick information or arrange a callback.</p>
              {!welcomed && <button onClick={begin} className="w-full border-t py-3 text-sm font-medium text-accent hover:bg-muted">Let’s Get Started</button>}
            </div>

            {msgs.map((m) => (
              <div key={m.id} className={m.from === "user" ? "flex flex-col items-end" : "flex flex-col items-start"}>
                <div className={m.from === "user" ? "max-w-[85%] whitespace-pre-line rounded-2xl rounded-br-sm bg-accent px-3 py-2 text-accent-foreground shadow-sm" : "max-w-[90%] whitespace-pre-line rounded-2xl rounded-bl-sm border bg-card px-3 py-2 shadow-sm"}>
                  {m.text}
                  {m.links && <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">{m.links.map((l) => <Link key={l.href} href={l.href} className="font-medium text-accent underline">{l.label}</Link>)}</div>}
                </div>
                <span className="mt-1 text-[11px] text-muted-foreground">{m.at}</span>
              </div>
            ))}
            {busy && <p className="text-xs text-muted-foreground">Sending…</p>}
            {chips.length > 0 && <div className="flex flex-wrap gap-2 pt-1">{chips.map((c) => <button key={c} disabled={busy} onClick={() => chip(c)} className="rounded-full border border-accent bg-card px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent hover:text-accent-foreground disabled:opacity-50">{c}</button>)}</div>}
          </div>
          <div className="border-t bg-card px-3 pb-2 pt-3">
            <form onSubmit={(e) => { e.preventDefault(); if (welcomed) route(input); }} className="flex items-center gap-2">
              <button type="button" onClick={showMenu} aria-label="Main menu" className="rounded-md border p-2 text-muted-foreground hover:bg-muted"><Menu className="h-5 w-5" /></button>
              <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} maxLength={255} disabled={busy || !welcomed} placeholder={!welcomed ? "Press “Let’s Get Started”" : step === "idle" ? "Ask a question…" : "Type your answer…"} aria-label="Your message" className="h-10 flex-1 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60" />
              <Button type="submit" size="icon" variant="accent" disabled={busy || !welcomed || !input.trim()} aria-label="Send"><Send className="h-4 w-4" /></Button>
            </form>
            <p className="pt-2 text-center text-[11px] text-muted-foreground">Not for emergencies (India: 112). Please don’t share medical details here.</p>
          </div>
        </div>
      )}
    </>
  );
}
