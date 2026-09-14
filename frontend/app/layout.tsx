import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Accord402",
  description:
    "Verifiable service covenants and finality-safe GEN settlement on GenLayer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
