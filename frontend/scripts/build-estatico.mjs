// Compila el frontend como sitio estático (carpeta `out/`) para subir a un hosting común (cPanel).
//
// Uso:   NEXT_PUBLIC_API_URL=https://api.tudominio.com npm run build:estatico
//   (PowerShell:  $env:NEXT_PUBLIC_API_URL="https://api.tudominio.com"; npm run build:estatico)
//
// La URL del backend queda escrita en los archivos al compilar: si cambia, hay que volver a compilar.
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const url = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
if (!url || !/^https?:\/\//.test(url)) {
  console.error("Falta NEXT_PUBLIC_API_URL (ej. https://api.tudominio.com), sin barra final.");
  process.exit(1);
}

const next = createRequire(import.meta.url).resolve("next/dist/bin/next");
const r = spawnSync(process.execPath, [next, "build"], {
  stdio: "inherit",
  env: { ...process.env, EXPORTAR_ESTATICO: "1", NEXT_PUBLIC_API_URL: url },
});
if (r.status === 0) console.log(`\nListo: subir el contenido de frontend/out/ al hosting (API: ${url}).`);
process.exit(r.status ?? 1);
