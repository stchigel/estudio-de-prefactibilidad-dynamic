"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { PasoConsumos } from "@/components/PasoConsumos";
import { PasoFacturas } from "@/components/PasoFacturas";
import { PasoOpciones } from "@/components/PasoOpciones";
import { PasoProyecto } from "@/components/PasoProyecto";
import { PasoResultados } from "@/components/PasoResultados";
import { Aviso, Boton } from "@/components/ui";
import { api, ErrorApi } from "@/lib/api";
import {
  aplicarSugerencias,
  borrarBorrador,
  entradasIniciales,
  guardarBorrador,
  leerBorrador,
  PASOS,
  type Paso,
} from "@/lib/estado";
import type { Entradas, OpcionesFormulario, RespuestaExtraccion } from "@/lib/tipos";

const sinSuscripcion = () => () => {};

export default function Inicio() {
  // El borrador vive en localStorage: el asistente se monta solo en el navegador.
  const enCliente = useSyncExternalStore(sinSuscripcion, () => true, () => false);
  return enCliente ? <Asistente /> : null;
}

function Asistente() {
  const [borrador] = useState(leerBorrador);
  const [paso, setPaso] = useState<Paso>(borrador?.paso ?? "Facturas");
  const [entradas, setEntradas] = useState<Entradas>(() => ({ ...entradasIniciales(), ...borrador?.entradas }));
  const [extraccion, setExtraccion] = useState<RespuestaExtraccion | null>(borrador?.extraccion ?? null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [opciones, setOpciones] = useState<OpcionesFormulario | null>(null);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);

  useEffect(() => {
    api
      .opciones()
      .then(setOpciones)
      .catch((e: ErrorApi) => setErrorCarga(e.message));
  }, []);

  useEffect(() => {
    guardarBorrador({ paso, entradas, extraccion });
  }, [paso, entradas, extraccion]);

  const actualizar = useCallback((c: Partial<Entradas>) => setEntradas((e) => ({ ...e, ...c })), []);
  const indice = PASOS.indexOf(paso);

  const nueva = () => {
    if (!confirm("¿Descartar la propuesta actual y empezar una nueva?")) return;
    borrarBorrador();
    setEntradas(entradasIniciales());
    setExtraccion(null);
    setArchivos([]);
    setPaso("Facturas");
  };

  return (
    <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-acento">Dynamic Energy</p>
          <h1 className="text-2xl font-semibold text-tinta">Estudio de prefactibilidad solar</h1>
        </div>
        <Boton variante="fantasma" onClick={nueva}>
          Nueva propuesta
        </Boton>
      </header>

      <nav aria-label="Pasos" className="mb-8">
        <ol className="flex flex-wrap gap-2">
          {PASOS.map((p, i) => {
            const activo = p === paso;
            const hecho = i < indice;
            return (
              <li key={p}>
                <button
                  type="button"
                  disabled={!hecho}
                  onClick={() => setPaso(p)}
                  aria-current={activo ? "step" : undefined}
                  className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition ${
                    activo
                      ? "border-acento bg-acento text-white"
                      : hecho
                        ? "border-borde bg-superficie text-tinta hover:border-acento"
                        : "border-borde text-tenue"
                  }`}
                >
                  <span className="tabular-nums">{i + 1}</span>
                  {p}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {errorCarga && (
        <div className="mb-6">
          <Aviso nivel="error">{errorCarga}</Aviso>
        </div>
      )}

      {paso === "Facturas" && (
        <PasoFacturas
          archivos={archivos}
          setArchivos={setArchivos}
          alExtraer={(r) => {
            setExtraccion(r);
            setEntradas((e) => aplicarSugerencias(e, r));
            setPaso("Consumos");
          }}
          alSaltear={() => setPaso("Consumos")}
        />
      )}
      {paso === "Consumos" && (
        <PasoConsumos
          consumos={entradas.consumos}
          alCambiar={(consumos) => actualizar({ consumos })}
          extraccion={extraccion}
          archivos={archivos}
          alConfirmar={() => setPaso("Proyecto")}
          alVolver={() => setPaso("Facturas")}
        />
      )}
      {paso === "Proyecto" && opciones && (
        <PasoProyecto
          e={entradas}
          opciones={opciones}
          alCambiar={actualizar}
          alContinuar={() => setPaso("Opciones")}
          alVolver={() => setPaso("Consumos")}
        />
      )}
      {paso === "Opciones" && opciones && (
        <PasoOpciones
          e={entradas}
          opciones={opciones}
          alElegir={(kit1, kit2) => {
            actualizar({ kit1, kit2 });
            setPaso("Resultados");
          }}
          alVolver={() => setPaso("Proyecto")}
        />
      )}
      {paso === "Resultados" && (
        <PasoResultados e={entradas} alCambiar={actualizar} alVolver={() => setPaso("Opciones")} alNueva={nueva} />
      )}
    </div>
  );
}
