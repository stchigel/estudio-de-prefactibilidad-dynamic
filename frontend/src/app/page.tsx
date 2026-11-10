"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { PantallaLogin } from "@/components/PantallaLogin";
import { PasoConsumos } from "@/components/PasoConsumos";
import { PasoFacturas } from "@/components/PasoFacturas";
import { PasoOpciones } from "@/components/PasoOpciones";
import { PasoProyecto } from "@/components/PasoProyecto";
import { PasoResultados } from "@/components/PasoResultados";
import { Aviso, Boton } from "@/components/ui";
import { api, ErrorApi, EVENTO_SESION_VENCIDA } from "@/lib/api";
import {
  aplicarSugerencias,
  borrarBorrador,
  entradasIniciales,
  entradasNuevoAnalisis,
  guardarBorrador,
  leerBorrador,
  PASOS,
  type Paso,
} from "@/lib/estado";
import type { Entradas, KitsOpcion, OpcionesFormulario, RespuestaExtraccion } from "@/lib/tipos";

const sinSuscripcion = () => () => {};

export default function Inicio() {
  // El borrador vive en localStorage: el asistente se monta solo en el navegador.
  const enCliente = useSyncExternalStore(sinSuscripcion, () => true, () => false);
  return enCliente ? <ControlAcceso /> : null;
}

/** Si la API tiene contraseña (publicada en internet) pide iniciar sesión; si no, entra directo. */
function ControlAcceso() {
  const [estado, setEstado] = useState<"comprobando" | "login" | "listo" | "error">("comprobando");
  const [requiereLogin, setRequiereLogin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .sesion()
      .then((s) => {
        setRequiereLogin(s.requiere_login);
        setEstado(s.autenticado ? "listo" : "login");
      })
      .catch((e: ErrorApi) => {
        setError(e.message);
        setEstado("error");
      });
    // Sesión vencida a mitad de trabajo: el borrador queda en localStorage y se recupera al volver a entrar.
    const alVencer = () => setEstado("login");
    window.addEventListener(EVENTO_SESION_VENCIDA, alVencer);
    return () => window.removeEventListener(EVENTO_SESION_VENCIDA, alVencer);
  }, []);

  const salir = () => {
    api.logout().finally(() => setEstado("login"));
  };

  if (estado === "comprobando") return null;
  if (estado === "error") {
    return (
      <div className="mx-auto w-full max-w-xl px-4 py-8">
        <Aviso nivel="error">{error}</Aviso>
      </div>
    );
  }
  if (estado === "login") return <PantallaLogin alEntrar={() => setEstado("listo")} />;
  return <Asistente alSalir={requiereLogin ? salir : undefined} />;
}

function Asistente({ alSalir }: { alSalir?: () => void }) {
  const [borrador] = useState(leerBorrador);
  const [paso, setPaso] = useState<Paso>(borrador?.paso ?? "Facturas");
  const [entradas, setEntradas] = useState<Entradas>(() => ({ ...entradasIniciales(), ...borrador?.entradas }));
  const [extraccion, setExtraccion] = useState<RespuestaExtraccion | null>(borrador?.extraccion ?? null);
  const [opcionesPpt, setOpcionesPpt] = useState<KitsOpcion[] | null>(borrador?.opcionesPpt ?? null);
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
    guardarBorrador({ paso, entradas, extraccion, opcionesPpt });
  }, [paso, entradas, extraccion, opcionesPpt]);

  const actualizar = useCallback((c: Partial<Entradas>) => setEntradas((e) => ({ ...e, ...c })), []);
  const indice = PASOS.indexOf(paso);

  const nueva = () => {
    if (!confirm("¿Descartar la propuesta actual y empezar una nueva?")) return;
    borrarBorrador();
    setEntradas(entradasNuevoAnalisis);
    setExtraccion(null);
    setOpcionesPpt(null);
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
        <div className="flex items-center gap-2">
          <Boton variante="fantasma" onClick={nueva}>
            Nueva propuesta
          </Boton>
          {alSalir && (
            <Boton variante="fantasma" onClick={alSalir}>
              Salir
            </Boton>
          )}
        </div>
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
            // Facturas nuevas = análisis nuevo: no se arrastran los datos del cliente anterior.
            setEntradas((e) => aplicarSugerencias(entradasNuevoAnalisis(e), r));
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
          sugerencias={extraccion?.sugerencias ?? null}
          alCambiar={actualizar}
          alContinuar={() => setPaso("Opciones")}
          alVolver={() => setPaso("Consumos")}
        />
      )}
      {paso === "Opciones" && opciones && (
        <PasoOpciones
          e={entradas}
          opciones={opciones}
          alElegir={(kit1, kit2, tildadas) => {
            actualizar({ kit1, kit2 });
            setOpcionesPpt(tildadas);
            setPaso("Resultados");
          }}
          alVolver={() => setPaso("Proyecto")}
        />
      )}
      {paso === "Resultados" && opciones && (
        <PasoResultados
          e={entradas}
          opciones={opciones}
          opcionesPpt={opcionesPpt}
          alCambiar={actualizar}
          alVolver={() => setPaso("Opciones")}
          alNueva={nueva}
        />
      )}
    </div>
  );
}
