import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";

import { FloatingNav } from "@/components/floating-nav";
import "./globals.css";

const nunito = Nunito({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "TinyGuide AI — Your Parenting Companion",
  description:
    "A warm, AI-powered companion for tracking milestones, growth, and vaccinations.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#fef7f1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={nunito.variable}>
      <body className="min-h-dvh font-sans">
        {/* Centered mobile-first column. */}
        <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pb-28 pt-6">
          {children}
        </div>
        <FloatingNav />
      </body>
    </html>
  );
}
