import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Studio Yofamo",
  description: "Kantor virtual tim agent pabrik Shorts Yofamo Technology",
  icons: { icon: "/favicon.svg" },
};
export const viewport: Viewport = { themeColor: "#0e1b2e", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
