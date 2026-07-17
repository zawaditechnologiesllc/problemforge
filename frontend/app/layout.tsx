import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "ProblemForge — Find Validated Problems from Expired Patents",
    template: "%s — ProblemForge",
  },
  description:
    "Every Idea Blueprint is backed by real, now-public-domain engineering logic mined from expired patents — translated into plain language with a ready-to-paste master prompt for Cursor and Windsurf.",
};

export const viewport = {
  themeColor: "#0F1115",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="flex min-h-screen flex-col font-sans">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
