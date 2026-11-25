"use client";

import { Check } from "lucide-react";
import { Fragment } from "react";
import { PASOS, type Paso } from "@/lib/estado";

/** Indicador de pasos: los anteriores se pueden revisitar; el actual va resaltado; los siguientes, apagados. */
export function Pasos({ paso, alElegir }: { paso: Paso; alElegir: (p: Paso) => void }) {
  const indice = PASOS.indexOf(paso);
  return (
    <nav aria-label="Pasos" className="order-last w-full xl:order-none xl:w-auto xl:flex-1">
      <ol className="flex items-center">
        {PASOS.map((p, i) => {
          const activo = p === paso;
          const hecho = i < indice;
          return (
            <Fragment key={p}>
              <li className="shrink-0">
                <button
                  type="button"
                  disabled={!hecho}
                  onClick={() => alElegir(p)}
                  aria-current={activo ? "step" : undefined}
                  className="group flex items-center gap-2 rounded-md py-1 pl-1 pr-2 text-sm transition-colors duration-150 enabled:hover:bg-superficie-2 disabled:cursor-default"
                >
                  <span
                    className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums transition-colors duration-150 ${
                      activo
                        ? "bg-acento text-sobre-acento"
                        : hecho
                          ? "bg-acento-suave text-acento ring-1 ring-inset ring-acento/30"
                          : "text-tenue ring-1 ring-inset ring-borde-fuerte"
                    }`}
                  >
                    {hecho ? <Check aria-hidden className="size-3.5" strokeWidth={3} /> : i + 1}
                  </span>
                  <span
                    className={`${activo ? "font-medium text-tinta" : hecho ? "hidden text-tinta-2 group-hover:text-tinta md:inline" : "hidden text-tenue md:inline"}`}
                  >
                    {p}
                  </span>
                  {hecho && <span className="sr-only"> (completado)</span>}
                </button>
              </li>
              {i < PASOS.length - 1 && (
                <li aria-hidden className={`mx-1 h-px min-w-3 flex-1 ${hecho ? "bg-acento/45" : "bg-borde-fuerte"}`} />
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
