"use client";

import { Presentation } from "lucide-react";
import { useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import type { DiapositivaPpt, Entradas, KitsOpcion } from "@/lib/tipos";
import { Aviso, Boton, Seccion } from "./ui";

type Imagen = "logo" | "planta" | "montaje";

const IMAGENES: { clave: Imagen; etiqueta: string; ayuda: string }[] = [
  { clave: "logo", etiqueta: "Logo del cliente", ayuda: "Portada" },
  { clave: "planta", etiqueta: "Foto de la planta", ayuda: "El objetivo" },
  { clave: "montaje", etiqueta: "Foto del montaje", ayuda: "La oportunidad detectada" },
];

// Texto de la línea CFI que llevan las presentaciones de ejemplo; se puede editar o vaciar (sin texto no sale el bloque).
const TEXTO_CFI_POR_DEFECTO = [
  "Plazos hasta 60 meses con 1 año de Gracia sobre capital y tasas fijas del 21% los primeros 2 años y Tamar + 2pp para el resto.",
  "1% de gastos administrativos",
  "Hasta el 80% de la inversion y un máximo de 500 M$ar.",
  "",
  "Ejemplo con el incremento de Tarifa electrica =TAMAR=cotización del Dolar",
].join("\n");

const claseTexto =
  "w-full rounded-md border border-borde-fuerte bg-superficie px-3 py-2 text-sm leading-5 text-tinta outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-tenue hover:border-eje focus:border-acento focus:ring-3 focus:ring-acento/20";

/** Miniatura genérica de una diapositiva (marcador; no refleja el contenido real). */
function Miniatura({ numero, apagada }: { numero: number; apagada: boolean }) {
  return (
    <span
      aria-hidden
      className={`relative flex aspect-video w-28 shrink-0 flex-col gap-1.5 overflow-hidden rounded-md border border-borde bg-plano p-2 transition-opacity duration-150 ${
        apagada ? "opacity-50 grayscale" : ""
      }`}
    >
      <span className="h-1.5 w-3/5 rounded-full bg-tinta-2/45" />
      <span className="flex flex-1 gap-1.5">
        <span className="flex flex-1 flex-col gap-1 pt-0.5">
          <span className="h-1 w-full rounded-full bg-eje" />
          <span className="h-1 w-4/5 rounded-full bg-eje" />
          <span className="h-1 w-2/3 rounded-full bg-eje" />
        </span>
        <span className="w-2/5 rounded-sm bg-acento/25" />
      </span>
      <span className="absolute bottom-1 right-1.5 text-[9px] font-medium leading-none text-tenue tabular-nums">{numero}</span>
    </span>
  );
}

export function SeccionPresentacion({
  e,
  diapositivas,
  opcionesPpt,
}: {
  e: Entradas;
  diapositivas: DiapositivaPpt[];
  opcionesPpt: KitsOpcion[] | null;
}) {
  const [imagenes, setImagenes] = useState<Partial<Record<Imagen, File>>>({});
  const [excluidas, setExcluidas] = useState<Set<number>>(new Set());
  const [textoBancario, setTextoBancario] = useState("");
  const [textoCfi, setTextoCfi] = useState(TEXTO_CFI_POR_DEFECTO);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alternar = (numero: number) =>
    setExcluidas((previas) => {
      const nuevas = new Set(previas);
      if (!nuevas.delete(numero)) nuevas.add(numero);
      return nuevas;
    });

  const generar = async () => {
    setGenerando(true);
    setError(null);
    try {
      await api.exportarPpt(e, {
        opcionesIncluidas: opcionesPpt,
        diapositivasExcluidas: [...excluidas].sort((a, b) => a - b),
        textoBancario,
        textoCfi,
        imagenes,
      });
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
        <Boton onClick={generar} cargando={generando} icono={<Presentation aria-hidden />}>
          Descargar PowerPoint
        </Boton>
      }
    >
      <div className="grid gap-4 lg:grid-cols-3">
        {IMAGENES.map(({ clave, etiqueta, ayuda }) => (
          <label key={clave} className="flex flex-col gap-1.5 text-sm">
            <span className="text-[13px] font-medium text-tinta-2">{etiqueta}</span>
            <input
              type="file"
              accept="image/png,image/jpeg"
              className="w-full cursor-pointer rounded-md border border-borde-fuerte bg-superficie text-sm text-tinta-2 transition-colors hover:border-eje file:mr-3 file:h-9 file:cursor-pointer file:border-0 file:border-r file:border-borde-fuerte file:bg-superficie-2 file:px-3 file:text-sm file:font-medium file:text-tinta"
              onChange={(ev) => setImagenes({ ...imagenes, [clave]: ev.target.files?.[0] })}
            />
            <span className="text-xs text-tenue">{imagenes[clave] ? imagenes[clave]!.name : `Opcional · diapositiva "${ayuda}"`}</span>
          </label>
        ))}
      </div>

      <fieldset className="mt-6 border-t border-borde pt-5">
        <legend className="sr-only">Páginas de la presentación</legend>
        <div className="mb-2 flex w-full items-center justify-between text-[13px] font-medium text-tinta-2">
          <span aria-hidden>
            Páginas de la presentación
            <span className="ml-2 font-normal text-tenue tabular-nums">
              {diapositivas.length - excluidas.size} de {diapositivas.length}
            </span>
          </span>
          <span className="flex gap-3 text-xs font-normal">
            <button type="button" className="rounded font-medium text-acento underline-offset-2 hover:underline" onClick={() => setExcluidas(new Set())}>
              Todas
            </button>
            <button
              type="button"
              className="rounded font-medium text-acento underline-offset-2 hover:underline"
              onClick={() => setExcluidas(new Set(diapositivas.map((d) => d.numero)))}
            >
              Ninguna
            </button>
          </span>
        </div>
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {diapositivas.map((d) => {
            const incluida = !excluidas.has(d.numero);
            return (
              <li key={d.numero}>
                <label
                  className={`relative flex h-full cursor-pointer gap-3 rounded-lg border p-2.5 transition-colors duration-150 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-acento ${
                    incluida ? "border-borde-fuerte bg-superficie hover:border-acento/60" : "border-borde bg-superficie-2/60 hover:border-borde-fuerte"
                  }`}
                >
                  <Miniatura numero={d.numero} apagada={!incluida} />
                  <span className="flex min-w-0 flex-1 flex-col py-0.5 pr-6">
                    <span className="text-xs text-tenue tabular-nums">Diapositiva {d.numero}</span>
                    <span className={`text-sm font-medium leading-5 ${incluida ? "text-tinta" : "text-tenue"}`}>{d.titulo}</span>
                    {d.nota && <span className="mt-0.5 text-xs leading-4 text-tenue">{d.nota}</span>}
                  </span>
                  <input
                    type="checkbox"
                    className="absolute right-2.5 top-2.5"
                    checked={incluida}
                    onChange={() => alternar(d.numero)}
                  />
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>

      <div className="mt-6 grid gap-4 border-t border-borde pt-5 lg:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-[13px] font-medium text-tinta-2">Texto CFI (financiamiento propio)</span>
          <textarea rows={6} value={textoCfi} onChange={(ev) => setTextoCfi(ev.target.value)} className={claseTexto} />
          <span className="text-xs text-tenue">Una línea por renglón. Vacío = no se muestra el bloque CFI.</span>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-[13px] font-medium text-tinta-2">Financiación bancaria</span>
          <textarea
            rows={6}
            value={textoBancario}
            onChange={(ev) => setTextoBancario(ev.target.value)}
            placeholder="Opcional. Si se completa, se agrega la diapositiva de financiación bancaria."
            className={claseTexto}
          />
        </label>
      </div>
      <p className="mt-4 text-xs text-tenue">
        Sin imágenes quedan los marcadores de la plantilla para completarlos a mano. La tabla de opciones usa las tildadas en el paso
        anterior.
      </p>
      {error && (
        <div className="mt-3">
          <Aviso nivel="error">{error}</Aviso>
        </div>
      )}
    </Seccion>
  );
}
