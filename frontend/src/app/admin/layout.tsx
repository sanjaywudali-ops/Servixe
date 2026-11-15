import { Shell } from "@/components/shell";

const nav = [
  { href: "/admin", label: "Operations overview", exact: true },
  { href: "/admin/requests", label: "Requests" },
  { href: "/admin/enquiries", label: "Enquiries" },
  { href: "/admin/customers", label: "Customers & families" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/incidents", label: "Incident desk" },
  { href: "/admin/finance", label: "Finance" },
  { href: "/admin/reports", label: "Reports" },
  { href: "/admin/catalogue", label: "Catalogue & pricing", adminOnly: true },
  { href: "/admin/audit", label: "Audit trail", adminOnly: true },
  { href: "/admin/staff", label: "Staff", adminOnly: true },
];
export default function Layout({ children }: { children: React.ReactNode }) {
  return <Shell roles={["support", "admin"]} nav={nav} title="Operations">{children}</Shell>;
}
