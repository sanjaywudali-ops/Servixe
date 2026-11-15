import { Shell } from "@/components/shell";

const nav = [
  { href: "/portal", label: "Dashboard", exact: true },
  { href: "/portal/parents", label: "My parents" },
  { href: "/portal/requests", label: "Requests" },
  { href: "/portal/invoices", label: "Invoices" },
  { href: "/portal/account", label: "Account" },
];
export default function Layout({ children }: { children: React.ReactNode }) {
  return <Shell roles={["customer"]} nav={nav} title="Family portal">{children}</Shell>;
}
