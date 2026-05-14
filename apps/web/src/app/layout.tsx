import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "FactGuard — Video Fact Checking",
  description:
    "Verify YouTube videos and uploads. Per-sentence checkworthy point extraction, live DuckDuckGo evidence retrieval, Qdrant Cloud Inference reranking, and a cited overall summary.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-bg text-fg">{children}</body>
    </html>
  );
}
