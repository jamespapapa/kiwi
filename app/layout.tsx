import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "kiwi | ultrawork Console for SSLife.",
  description: "ultrawork Console for Samsung Life Insurance platform development.",
  icons: {
    icon: [
      {
        url: "/icon.svg",
        type: "image/svg+xml"
      }
    ],
    shortcut: "/icon.svg",
    apple: "/icon.svg"
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
