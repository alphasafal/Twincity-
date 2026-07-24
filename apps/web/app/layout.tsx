import type { Metadata } from "next";
import { IBM_Plex_Mono, Source_Sans_3, Syne } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { AppProviders } from "@/lib/providers";
import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "TwinPilot — Autonomous building optimization you can verify",
    template: "%s · TwinPilot",
  },
  description:
    "Sellable B2B SaaS for safe building energy optimization. AI proposes, Safety Shield validates, operators approve. BACnet, Modbus, and Honeywell-ready.",
  openGraph: {
    title: "TwinPilot",
    description: "Autonomous optimization you can verify.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${sourceSans.variable} ${ibmPlexMono.variable} ${syne.variable} font-sans antialiased`}
      >
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
