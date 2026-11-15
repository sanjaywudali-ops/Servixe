import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { RegisterSW } from "@/components/register-sw";

export const metadata: Metadata = {
  title: { default: "Servixe — trusted local support for your parents", template: "%s · Servixe" },
  description: "Servixe coordinates non-clinical parent-support services through verified local partners in Nellore, Andhra Pradesh, for families living overseas.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg", apple: "/icons/icon-192.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#1a3550" }, { media: "(prefers-color-scheme: dark)", color: "#0e1a26" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-card focus:p-3">Skip to content</a>
        <AuthProvider>{children}</AuthProvider>
        <RegisterSW />
      </body>
    </html>
  );
}
