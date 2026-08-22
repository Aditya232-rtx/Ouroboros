import type { Metadata } from "next";
import { GeistMono } from "geist/font/mono";
import "@fontsource/geist-pixel";
import "./globals.css";
import "../components/ouro-ui/ouro-index.css";

export const metadata: Metadata = {
  title: "Ouroboros | Autonomous AI Security",
  description:
    "Ouroborous — The infinite cycle of AI intelligence. We build self-evolving AI systems that continuously learn, adapt, and transcend.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={GeistMono.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Jersey+25&family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Silkscreen:wght@400;700&family=Spectral:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=UnifrakturMaguntia&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
