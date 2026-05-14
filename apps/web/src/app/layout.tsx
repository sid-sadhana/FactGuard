import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "FactGuard — Video Fact Checking",
  description:
    "Verify YouTube videos and uploads with vision-language frame analysis, transcript-grounded claim extraction, and cited web evidence.",
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
