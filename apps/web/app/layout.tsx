import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600"],
});

const body = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "ContextIQ",
    template: "%s · ContextIQ",
  },
  description:
    "Eval-first RAG platform for production knowledge and support systems",
};

const nav = [
  { href: "/", label: "Home" },
  { href: "/chat", label: "Demo" },
  { href: "/eval", label: "Eval" },
  { href: "/failures", label: "Failures" },
  { href: "/traces", label: "Traces" },
  { href: "/architecture", label: "Architecture" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>
        <div className="min-h-screen">
          <nav className="border-b border-line/80 bg-paper-elev/70 backdrop-blur-sm">
            <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
              <Link href="/" className="font-display text-lg font-semibold tracking-tight text-ink">
                ContextIQ
              </Link>
              <div className="flex items-center gap-4 text-sm font-semibold text-ink-muted">
                {nav.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="transition-colors hover:text-accent"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
