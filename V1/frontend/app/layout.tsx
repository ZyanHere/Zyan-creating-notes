import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MyNotes",
  // What a browser tab and a link preview say. The old one described this as a
  // "dashboard mock UI", which is what anyone opening the deployed app read.
  description:
    "Say what you need to learn. MyNotes plans it, shows you the plan, and only "
    + "writes once you approve — one PDF per module.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
