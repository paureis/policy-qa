import type { Metadata } from "next";
import { Archivo } from "next/font/google";
import "./globals.css";

/* Archivo, variable in weight and width: normal width for the page, the wdth axis condenses the stamp. */
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
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
    <html lang="en" className={`${archivo.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-manila text-ink">
        <InkFilter />
        {children}
      </body>
    </html>
  );
}

/*
  The rubber stamp's uneven ink (.stamp in globals.css): fine noise punches
  small holes in the ink, a slow noise fades whole patches, and a slight
  displacement roughens the edges. Defined once for every page.
*/
function InkFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
      <defs>
        <filter id="ink-stamp" x="-5%" y="-10%" width="110%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={7} result="n" />
          <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.3 1.45" result="holes" />
          <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves={1} seed={3} result="w" />
          <feColorMatrix in="w" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.1 1.6" result="fade" />
          <feComposite in="SourceGraphic" in2="holes" operator="in" result="a" />
          <feComposite in="a" in2="fade" operator="in" result="b" />
          <feDisplacementMap in="b" in2="n" scale={2} />
        </filter>
      </defs>
    </svg>
  );
}
