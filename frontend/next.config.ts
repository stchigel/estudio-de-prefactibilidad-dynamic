import type { NextConfig } from "next";

// Dos modos:
//  - Normal (desarrollo y uso en una PC): el navegador habla solo con este servidor (puerto 3000) y las
//    llamadas a /api se reenvían al backend, que puede quedar en 127.0.0.1 sin exponerse a la red.
//  - Estático (EXPORTAR_ESTATICO=1, ver `npm run build:estatico`): genera archivos HTML/JS en `out/` para subir a
//    un hosting común (cPanel). No hay servidor Next, así que el navegador llama directo al backend, cuya URL
//    se fija al compilar con NEXT_PUBLIC_API_URL.
const ESTATICO = process.env.EXPORTAR_ESTATICO === "1";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  ...(ESTATICO
    ? {
        output: "export",
        // Carpeta propia para no pisar el `.next` del modo normal.
        distDir: ".next-export",
      }
    : {
        cacheComponents: true,
        partialPrefetching: true,
        // En `next dev`, orígenes distintos de localhost desde los que se abre la aplicación
        // (IP de Tailscale de esta PC). Sin esto Next bloquea los scripts y la página queda en blanco.
        allowedDevOrigins: ["100.92.110.14"],
        async rewrites() {
          return [{ source: "/api/:ruta*", destination: `${BACKEND_URL}/api/:ruta*` }];
        },
        experimental: {
          // La lectura de facturas con IA puede tardar más que los 30 s por defecto del reenvío.
          proxyTimeout: 300_000,
        },
      }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
