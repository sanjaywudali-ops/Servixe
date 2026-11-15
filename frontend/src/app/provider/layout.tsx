"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardList, History, LogOut, User } from "lucide-react";
import { EmergencyBanner } from "@/components/common";
import { Logo } from "@/components/site-header";
import { RequireRole, useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "/provider", label: "Jobs", icon: ClipboardList, exact: true },
  { href: "/provider/history", label: "History", icon: History },
  { href: "/provider/profile", label: "Profile", icon: User },
];

export default function ProviderLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  return (
    <RequireRole roles={["provider"]}>
      <EmergencyBanner />
      <div className="mx-auto flex min-h-screen max-w-xl flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4"><Logo />
          <button aria-label="Sign out" className="flex items-center gap-1 text-sm" onClick={async () => { await logout(); router.replace("/login"); }}><LogOut className="h-4 w-4" /> Sign out</button></header>
        <main id="main" className="flex-1 p-4 pb-24">{children}</main>
        <nav aria-label="Provider" className="fixed inset-x-0 bottom-0 z-30 border-t bg-background pb-[env(safe-area-inset-bottom)]">
          <ul className="mx-auto grid max-w-xl grid-cols-3">
            {tabs.map(({ href, label, icon: Icon, exact }) => {
              const on = exact ? path === href : path.startsWith(href) || (href === "/provider" && path.startsWith("/provider/jobs"));
              return <li key={href}><Link href={href} className={cn("flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs", on ? "font-semibold text-accent" : "text-muted-foreground")}><Icon className="h-5 w-5" aria-hidden />{label}</Link></li>;
            })}
          </ul>
        </nav>
      </div>
    </RequireRole>
  );
}
