import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import "./globals.css";
import "./theme.css";

export const metadata: Metadata = {
  title: { default: "Digital Product Passport", template: "%s · AAS DPP" },
  description: "Live Asset Administration Shell product passport viewer.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#f7f8f8" };

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body><AppShell>{children}</AppShell></body></html>;
}
