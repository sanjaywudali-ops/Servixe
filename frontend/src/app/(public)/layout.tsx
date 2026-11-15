import { EmergencyBanner } from "@/components/common";
import { SiteFooter, SiteHeader } from "@/components/site-header";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <EmergencyBanner />
      <SiteHeader />
      <main id="main">{children}</main>
      <SiteFooter />
    </>
  );
}
