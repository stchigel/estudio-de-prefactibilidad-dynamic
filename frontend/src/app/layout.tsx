import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prefactibilidad Solar · Dynamic Energy",
  description: "Estudios de prefactibilidad solar: facturas, cálculo, opciones y exportes",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es-AR" className="h-full antialiased">
      {/* suppressHydrationWarning: extensiones del navegador (ColorZilla, temas) inyectan atributos en <body> */}
      <body className="flex min-h-full flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
