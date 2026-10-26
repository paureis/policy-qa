import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";
import "./globals.css";

const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Recourse",
    template: "%s | Recourse",
  },
  description:
    "A coverage denial becomes a case, and the case works itself. Read a denial letter into a case card, check the details, and start the appeal.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${publicSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-bond text-ink">{children}</body>
    </html>
  );
}
