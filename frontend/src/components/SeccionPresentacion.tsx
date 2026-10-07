"use client";

import { useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import type { Entradas } from "@/lib/tipos";
import { Aviso, Boton, Seccion, SiNo } from "./ui";

type Imagen = "logo" | "planta" | "montaje";

const IMAGENES: { clave: Imagen; etiqueta: string; ayuda: string }[] = [
  { clave: "logo", etiqueta: "Logo del cliente", ayuda: "Portada" },
  { clave: "planta", etiqueta: "Foto de la planta", ayuda: "El objetivo" },
  { clave: "montaje", etiqueta: "Foto del montaje", ayuda: "La oportunidad detectada" },
];

export function SeccionPresentacion({ e }: { e: Entradas }) {
  const [imagenes, setImagenes] = useState<Partial<Record<Imagen, File>>>({});
  const [incluirOpciones, setIncluirOpciones] = useState(true);
  const [textoBancario, setTextoBancario] = useState("");
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generar = async () => {
    setGenerando(true);
    setError(null);
    try {
      await api.exportarPpt(e, { incluirOpciones, textoBancario, imagenes });
    } catch (err) {
      setError((err as ErrorApi).message);
    } finally {
      setGenerando(false);
    }
  };

  return (
    <Seccion
      titulo="Presentación"
      accion={
        <Boton onClick={generar} cargando={generando}>
          Descargar PowerPoint
        </Boton>
      }
    >
      <div className="grid gap-4 lg:grid-cols-3">
        {IMAGENES.map(({ clave, etiqueta, ayuda }) => (
          <label key={clave} className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-tinta-2">{etiqueta}</span>
            <input
              type="file"
              accept="image/png,image/jpeg"
              className="text-sm text-tinta-2 file:mr-3 file:rounded-md file:border file:border-borde file:bg-plano file:px-3 file:py-1.5 file:text-sm file:text-tinta"
              onChange={(ev) => setImagenes({ ...imagenes, [clave]: ev.target.files?.[0] })}
            />
            <span className="text-xs text-tenue">{imagenes[clave] ? imagenes[clave]!.name : `Opcional · diapositiva "${ayuda}"`}</span>
          </label>
        ))}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <fieldset className="flex flex-col gap-1 text-sm">
          <legend className="mb-1 font-medium text-tinta-2">Incluir tabla de opciones</legend>
          <SiNo valor={incluirOpciones} alCambiar={setIncluirOpciones} />
          <span className="text-xs text-tenue">Compara las opciones automáticas con la elegida</span>
        </fieldset>
        <label className="flex flex-col gap-1 text-sm lg:col-span-2">
          <span className="font-medium text-tinta-2">Financiación bancaria</span>
          <textarea
            rows={3}
            value={textoBancario}
            onChange={(ev) => setTextoBancario(ev.target.value)}
            placeholder="Opcional. Si se completa, se agrega la diapositiva de financiación bancaria (ej. línea CFI)."
            className="w-full rounded-md border border-borde bg-plano px-3 py-2 text-sm text-tinta outline-none focus:border-acento focus:ring-2 focus:ring-acento/30"
          />
        </label>
      </div>
      <p className="mt-3 text-xs text-tenue">
        Sin imágenes quedan los marcadores de la plantilla para completarlos a mano. La diapositiva de financiación propia se incluye si
        hay un porcentaje a financiar.
      </p>
      {error && (
        <div className="mt-3">
          <Aviso nivel="error">{error}</Aviso>
        </div>
      )}
    </Seccion>
  );
}
