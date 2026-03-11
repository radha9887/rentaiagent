import type { Metadata } from "next";
import "./globals.css";
import { ClientLayout } from "./client-layout";

export const metadata: Metadata = {
  title: "RentAnAgent",
  description: "Agent marketplace dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0a0a0b] text-white antialiased">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
