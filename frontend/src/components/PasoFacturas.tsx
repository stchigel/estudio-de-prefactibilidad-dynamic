"use client";

import { useRef, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import type { RespuestaExtraccion } from "@/lib/tipos";
import { Aviso, Boton, Seccion } from "./ui";

const ACEPTADOS = ["application/pdf", "image/jpeg", "image/png", "image/webp"];

export function PasoFacturas({
  archivos,
  setArchivos,
  alExtraer,
  alSaltear,
}: {
  archivos: File[];
  setArchivos: (a: File[]) => void;
  alExtraer: (r: RespuestaExtraccion) => void;
  alSaltear: () => void;
}) {
  const [arrastrando, setArrastrando] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const entrada = useRef<HTMLInputElement>(null);

  const agregar = (lista: FileList | null) => {
    if (!lista) return;
    const nuevos = Array.from(lista).filter((f) => ACEPTADOS.includes(f.type));
    const rechazados = lista.length - nuevos.length;
    setError(rechazados ? `${rechazados} archivo(s) ignorados: solo PDF, JPG o PNG.` : null);
    setArchivos([...archivos, ...nuevos]);
  };

  const extraer = async () => {
    setCargando(true);
    setError(null);
    try {
      alExtraer(await api.extraerFacturas(archivos));
    } catch (e) {
      const err = e as ErrorApi;
      setError(
        err.estado === 503
          ? `La lectura automática no está configurada: ${err.message}. Podés seguir y cargar los consumos a mano.`
          : err.message,
      );
    } finally {
      setCargando(false);
    }
  };

  return (
    <Seccion titulo="Facturas de luz del cliente">
      <p className="mb-4 text-sm text-tinta-2">
        Subí las facturas de la distribuidora (PDF, escaneos o fotos). Con dos facturas EPE se cubre el año; si faltan meses se
        estiman por espejo respecto del solsticio.
      </p>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          agregar(e.dataTransfer.files);
        }}
        onClick={() => entrada.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-12 text-center transition ${
          arrastrando ? "border-acento bg-acento/5" : "border-borde hover:border-acento/60"
        }`}
      >
        <span className="text-sm font-medium text-tinta">Arrastrá las facturas acá o hacé clic para elegirlas</span>
        <span className="text-xs text-tenue">PDF, JPG o PNG · hasta 30 MB cada una</span>
        <input
          ref={entrada}
          type="file"
          multiple
          accept={ACEPTADOS.join(",")}
          className="hidden"
          onChange={(e) => {
            agregar(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {archivos.length > 0 && (
        <ul className="mt-4 divide-y divide-borde rounded-md border border-borde">
          {archivos.map((a, i) => (
            <li key={`${a.name}-${i}`} className="flex items-center justify-between px-4 py-2 text-sm">
              <span className="truncate text-tinta">{a.name}</span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-tenue tabular-nums">{(a.size / 1024).toFixed(0)} KB</span>
                <button
                  className="text-xs text-tinta-2 hover:text-critico"
                  onClick={() => setArchivos(archivos.filter((_, j) => j !== i))}
                  aria-label={`Quitar ${a.name}`}
                >
                  Quitar
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <div className="mt-4">
          <Aviso nivel="error">{error}</Aviso>
        </div>
      )}

      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Boton variante="fantasma" onClick={alSaltear}>
          Cargar consumos a mano
        </Boton>
        <Boton onClick={extraer} deshabilitado={!archivos.length} cargando={cargando}>
          {cargando ? "Leyendo facturas…" : "Extraer datos"}
        </Boton>
      </div>
    </Seccion>
  );
}
