import type { NextConfig } from "next";

// El navegador habla solo con este servidor (puerto 3000); las llamadas a /api se reenvían al
// backend, que puede quedar escuchando en 127.0.0.1 sin exponerse a la red.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /* config options here */
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
