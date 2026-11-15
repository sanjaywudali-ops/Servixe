import { EmergencyBanner } from "@/components/common";
import { Logo } from "@/components/site-header";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <EmergencyBanner />
      <main id="main" className="container flex min-h-[80vh] flex-col items-center justify-center py-10">
        <Logo className="mb-6" />
        <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm">{children}</div>
      </main>
    </>
  );
}
