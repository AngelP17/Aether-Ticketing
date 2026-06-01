import localFont from "next/font/local";
import ClientLayout from "@/components/client-layout";
import "./globals.css";
import type { Metadata } from "next";

const chakraPetch = localFont({
  src: [
    { path: "../../public/fonts/ChakraPetch-300.woff2", weight: "300", style: "normal" },
    { path: "../../public/fonts/ChakraPetch-400.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/ChakraPetch-500.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/ChakraPetch-600.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/ChakraPetch-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-chakra",
  display: "swap",
});

const jetbrainsMono = localFont({
  src: "../../public/fonts/JetBrainsMono-400.woff2",
  weight: "400 700",
  style: "normal",
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aether OpsCenter",
  description: "Operational Incident Intelligence and Decision Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${chakraPetch.variable} ${jetbrainsMono.variable}`}>
      <body>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
