"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { PantallaLogin } from "@/components/PantallaLogin";
import { PasoConsumos } from "@/components/PasoConsumos";
import { PasoFacturas } from "@/components/PasoFacturas";
import { PasoOpciones } from "@/components/PasoOpciones";
import { PasoProyecto } from "@/components/PasoProyecto";
import { PasoResultados } from "@/components/PasoResultados";
import { Aviso, Boton, Marca, SelectorTema } from "@/components/ui";
import { Pasos } from "@/components/Pasos";
import { FilePlus, LoaderCircle, LogOut } from "lucide-react";
import { api, ErrorApi, EVENTO_SESION_VENCIDA } from "@/lib/api";
import {
  aplicarSugerencias,
  borrarBorrador,
  entradasIniciales,
  entradasNuevoAnalisis,
  guardarBorrador,
  leerBorrador,
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
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 px-4 py-8">
        <Marca />
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
    <>
      <header className="sticky top-0 z-30 border-b border-borde bg-superficie">
        <div className="mx-auto flex w-full max-w-[1280px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 sm:px-6">
          <div className="min-w-0 flex-1 xl:flex-none">
            <Marca />
          </div>
          <div className="flex shrink-0 items-center gap-1.5 xl:order-last">
            <SelectorTema />
            <Boton variante="fantasma" onClick={nueva} icono={<FilePlus aria-hidden />}>
              <span className="hidden sm:inline">Nueva propuesta</span>
              <span className="sr-only sm:hidden">Nueva propuesta</span>
            </Boton>
            {alSalir && (
              <Boton variante="fantasma" onClick={alSalir} icono={<LogOut aria-hidden />}>
                <span className="hidden sm:inline">Salir</span>
                <span className="sr-only sm:hidden">Salir</span>
              </Boton>
            )}
          </div>
          <Pasos paso={paso} alElegir={setPaso} />
        </div>
      </header>

      <main key={paso} className="entrar mx-auto flex w-full max-w-[1280px] flex-1 flex-col px-4 pt-6 sm:px-6">
      {errorCarga && (
        <div className="mb-6">
          <Aviso nivel="error">{errorCarga}</Aviso>
        </div>
      )}

      {!opciones && !errorCarga && paso !== "Facturas" && paso !== "Consumos" && (
        <p className="flex items-center gap-2 py-10 text-sm text-tenue" role="status">
          <LoaderCircle aria-hidden className="size-4 animate-spin" />
          Cargando opciones del formulario…
        </p>
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
      </main>
    </>
  );
}
