import type { Metadata } from "next";
import { SCRIPT_TEMA } from "@/lib/tema";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prefactibilidad Solar · Dynamic Energy",
  description: "Estudios de prefactibilidad solar: facturas, cálculo, opciones y exportes",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: el script de tema fija data-theme antes de hidratar.
    <html lang="es-AR" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      {/* suppressHydrationWarning: extensiones del navegador (ColorZilla, temas) inyectan atributos en <body> */}
      <body className="flex min-h-full flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
