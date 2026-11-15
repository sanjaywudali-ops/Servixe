"use client";
import { useEffect } from "react";

/** Registers the service worker used by the provider PWA (app-shell caching only; API responses are never cached). */
export function RegisterSW() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);
  return null;
}
