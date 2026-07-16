import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AX Consulting Mission Control · SoloOS",
  description: "AI Native Company dashboard for AX Consulting, powered by SoloOS.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
