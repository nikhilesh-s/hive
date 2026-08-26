import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import "./globals.css";
import { Navigation } from "@/components/Navigation";

const plexSerif = IBM_Plex_Serif({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "HiveBlot - Protein Discovery Platform",
  description: "Mine the blots. Extract the truth. Search thousands of published western blot results instantly. Discover protein expression patterns across cell lines and conditions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" style={{ minHeight: '100vh' }}>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body
        className={`${plexSerif.variable} ${plexSans.variable} ${plexMono.variable}`}
        style={{ margin: 0, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}
      >
        <Navigation />
        <main style={{ flex: 1 }}>
          {children}
        </main>
      </body>
    </html>
  );
}
