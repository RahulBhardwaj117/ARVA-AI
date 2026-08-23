import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");

  return {
    metadataBase: new URL(`${protocol}://${host}`),
    title: {
      default: "ARVA AI — Autonomous Decision Intelligence",
      template: "%s | ARVA AI",
    },
    description:
      "Predict demand, optimize compute and automate explainable infrastructure decisions.",
    openGraph: {
      title: "ARVA AI — Autonomous Decision Intelligence",
      description:
        "A predictive, explainable and policy-governed control plane for AI compute infrastructure.",
      type: "website",
      images: [
        {
          url: "/og.png",
          width: 1536,
          height: 1024,
          alt: "ARVA AI autonomous decision intelligence",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "ARVA AI — Autonomous Decision Intelligence",
      description:
        "Predict demand. Optimize compute. Decide what happens next.",
      images: ["/og.png"],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
