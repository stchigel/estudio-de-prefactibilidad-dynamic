"use client";

import { FileText, FlaskConical, ImageIcon, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import { extraccionDePrueba } from "@/lib/datosDePrueba";
import type { RespuestaExtraccion } from "@/lib/tipos";
import { Aviso, BarraAcciones, Boton, Seccion } from "./ui";

const ACEPTADOS = ["application/pdf", "image/jpeg", "image/png", "image/webp"];

function tamano(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

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
    <div className="flex flex-1 flex-col gap-6">
      <div className="mx-auto w-full max-w-3xl">
        <Seccion titulo="Facturas de luz del cliente">
          <p className="mb-4 max-w-[68ch] text-sm text-tinta-2">
            Subí las facturas de la distribuidora (PDF, escaneos o fotos). Con dos facturas EPE se cubre el año; si faltan meses se
            estiman por espejo respecto del solsticio.
          </p>
          <button
            type="button"
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
            className={`flex w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-10 text-center transition-colors duration-150 ${
              arrastrando ? "border-acento bg-acento-suave" : "border-borde-fuerte bg-superficie-2/50 hover:border-acento/60 hover:bg-acento-suave/50"
            }`}
          >
            <span
              aria-hidden
              className={`flex size-10 items-center justify-center rounded-full ${arrastrando ? "bg-acento text-sobre-acento" : "bg-superficie text-tinta-2 ring-1 ring-borde"}`}
            >
              <Upload className="size-5" />
            </span>
            <span className="text-sm font-medium text-tinta">Arrastrá las facturas acá o hacé clic para elegirlas</span>
            <span className="text-xs text-tenue">PDF, JPG o PNG · hasta 30 MB cada una</span>
          </button>
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

          {archivos.length > 0 && (
            <ul className="mt-4 divide-y divide-borde overflow-hidden rounded-lg border border-borde">
              {archivos.map((a, i) => {
                const Icono = a.type === "application/pdf" ? FileText : ImageIcon;
                return (
                  <li key={`${a.name}-${i}`} className="flex items-center gap-3 px-3 py-2 text-sm">
                    <Icono aria-hidden className="size-4 shrink-0 text-tenue" />
                    <span className="min-w-0 flex-1 truncate text-tinta">{a.name}</span>
                    <span className="text-xs text-tenue tabular-nums">{tamano(a.size)}</span>
                    <button
                      type="button"
                      className="flex size-7 items-center justify-center rounded-md text-tenue transition-colors hover:bg-critico/10 hover:text-critico-texto"
                      onClick={() => setArchivos(archivos.filter((_, j) => j !== i))}
                      aria-label={`Quitar ${a.name}`}
                      title="Quitar"
                    >
                      <X aria-hidden className="size-4" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {error && (
            <div className="mt-4">
              <Aviso nivel="error">{error}</Aviso>
            </div>
          )}
        </Seccion>
      </div>

      <div className="flex-1" />
      <BarraAcciones>
        <div className="flex flex-wrap items-center gap-2">
          <Boton variante="fantasma" onClick={alSaltear}>
            Cargar consumos a mano
          </Boton>
          {/* TEMPORAL, solo para pruebas: salta la IA con datos inventados (ver lib/datosDePrueba.ts). */}
          <Boton
            variante="fantasma"
            onClick={() => alExtraer(extraccionDePrueba(archivos))}
            deshabilitado={cargando}
            icono={<FlaskConical aria-hidden />}
            titulo="Salta la lectura con IA y carga datos ficticios. Solo para pruebas."
          >
            Datos de prueba (sin IA)
          </Boton>
        </div>
        <Boton onClick={extraer} deshabilitado={!archivos.length} cargando={cargando}>
          {cargando ? "Leyendo facturas…" : "Extraer datos"}
        </Boton>
      </BarraAcciones>
    </div>
  );
}
