"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, Menu, X } from "lucide-react";
import { Logo } from "@/components/site-header";
import { EmergencyBanner } from "@/components/common";
import { RequireRole, useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface NavItem { href: string; label: string; exact?: boolean; adminOnly?: boolean }

export function Shell({ roles, nav, title, children }: { roles: Role[]; nav: NavItem[]; title: string; children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { me, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const active = (n: NavItem) => (n.exact ? path === n.href : path === n.href || path.startsWith(n.href + "/"));
  const links = (
    <nav aria-label={title} className="flex flex-col gap-1">
      {nav.filter((n) => !n.adminOnly || me?.role === "admin").map((n) => (
        <Link key={n.href} href={n.href} onClick={() => setOpen(false)}
          className={cn("rounded-md px-3 py-2 text-sm hover:bg-muted", active(n) && "bg-secondary font-semibold text-secondary-foreground")}>{n.label}</Link>
      ))}
    </nav>
  );
  return (
    <RequireRole roles={roles}>
      <EmergencyBanner />
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background px-4">
          <div className="flex items-center gap-3">
            <button className="md:hidden" aria-label="Menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
            <Logo /><span className="hidden text-sm text-muted-foreground sm:inline">· {title}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden sm:inline text-muted-foreground">{me?.full_name || me?.email}</span>
            <button className="flex items-center gap-1 rounded-md px-2 py-1.5 hover:bg-muted" onClick={async () => { await logout(); router.replace("/login"); }}><LogOut className="h-4 w-4" />Sign out</button>
          </div>
        </header>
        <div className="flex flex-1">
          <aside className="hidden w-56 shrink-0 border-r p-3 md:block">{links}</aside>
          {open && <aside className="absolute inset-x-0 top-[calc(2.5rem+3.5rem)] z-20 border-b bg-background p-3 shadow md:hidden">{links}</aside>}
          <main id="main" className="min-w-0 flex-1 p-4 md:p-6"><div className="mx-auto max-w-6xl">{children}</div></main>
        </div>
      </div>
    </RequireRole>
  );
}
