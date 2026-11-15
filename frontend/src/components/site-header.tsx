"use client";
import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { homeFor, useAuth } from "@/lib/auth";

export const Logo = ({ className = "" }: { className?: string }) => (
  <Link href="/" className={`flex items-center gap-2 font-bold text-navy text-lg ${className}`}>
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="hsl(var(--primary))" /><path d="M16 24s-7-4.6-7-10a4 4 0 0 1 7-2.4A4 4 0 0 1 23 14c0 5.400-7 10-7 10z" fill="hsl(var(--teal))" /></svg>
    Servixe
  </Link>
);

const links = [
  { href: "/services", label: "Services" },
  { href: "/pricing", label: "Pricing" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
  { href: "/faq", label: "FAQs" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { me, loading } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Logo />
        <nav aria-label="Main" className="hidden items-center gap-6 text-sm md:flex">
          {links.map((l) => <Link key={l.href} href={l.href} className="hover:text-accent">{l.label}</Link>)}
        </nav>
        <div className="hidden items-center gap-2 md:flex">
          {!loading && me ? (
            <Button asChild size="sm"><Link href={homeFor(me.role)}>Open my account</Link></Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm"><Link href="/login">Sign in</Link></Button>
              <Button asChild variant="accent" size="sm"><Link href="/register">Create account</Link></Button>
            </>
          )}
        </div>
        <button className="md:hidden p-2" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open && (
        <nav aria-label="Mobile" className="container flex flex-col gap-1 border-t pb-4 pt-2 md:hidden">
          {links.map((l) => <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-md px-2 py-2.5 hover:bg-muted">{l.label}</Link>)}
          <div className="mt-2 flex gap-2">
            <Button asChild variant="outline" className="flex-1"><Link href="/login">Sign in</Link></Button>
            <Button asChild variant="accent" className="flex-1"><Link href="/register">Create account</Link></Button>
          </div>
        </nav>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t bg-secondary/50">
      <div className="container grid gap-8 py-10 text-sm md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo />
          <p className="mt-3 max-w-md text-muted-foreground">
            Servixe coordinates non-clinical parent-support services through verified local partners. We do not provide regulated clinical care,
            make medical decisions, interpret medical reports or guarantee emergency response.
          </p>
        </div>
        <div>
          <h4 className="mb-2 font-semibold">Explore</h4>
          <ul className="space-y-1.5 text-muted-foreground">
            {links.map((l) => <li key={l.href}><Link href={l.href} className="hover:text-accent">{l.label}</Link></li>)}
          </ul>
        </div>
        <div>
          <h4 className="mb-2 font-semibold">Legal</h4>
          <ul className="space-y-1.5 text-muted-foreground">
            <li><Link href="/privacy" className="hover:text-accent">Privacy notice</Link></li>
            <li><Link href="/terms" className="hover:text-accent">Terms &amp; refunds</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t py-4 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} Servixe. Pilot service area: Nellore, Andhra Pradesh, India.
      </div>
    </footer>
  );
}
