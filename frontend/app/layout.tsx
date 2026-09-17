import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Accord402 — Proof-bound agreements",
  description:
    "Verifiable service covenants and finality-safe GEN settlement on GenLayer Bradbury.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.documentElement.dataset.theme=localStorage.getItem('accord402-theme')||'light'",
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
