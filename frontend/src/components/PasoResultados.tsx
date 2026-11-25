"use client";

import { ArrowLeft, FilePlus, FileSpreadsheet, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import { fmt } from "@/lib/estado";
import type { Entradas, KitsOpcion, OpcionesFormulario, Resultado } from "@/lib/tipos";
import { GraficoFinanciacion, GraficoMensual, GraficoRoi } from "./Graficos";
import { describirKits } from "./PasoOpciones";
import { SeccionPresentacion } from "./SeccionPresentacion";
import { Aviso, BarraAcciones, Boton, Campo, Numero, Seccion, SiNo } from "./ui";

function Kpi({ etiqueta, valor, detalle, destacado }: { etiqueta: string; valor: string; detalle?: string; destacado?: boolean }) {
  return (
    <div className="flex flex-col bg-superficie px-4 py-3.5">
      <dt className="text-[13px] text-tinta-2">{etiqueta}</dt>
      <dd className={`mt-1 font-semibold tracking-[-0.01em] text-tinta tabular-nums ${destacado ? "text-2xl" : "text-lg"}`}>{valor}</dd>
      {detalle && <dd className="mt-0.5 text-xs text-tenue tabular-nums">{detalle}</dd>}
    </div>
  );
}

/** Grupo de indicadores separados por líneas finas; en pantallas angostas el último ocupa el renglón entero. */
function GrupoKpi({ children }: { children: React.ReactNode }) {
  return <dl className="grid grid-cols-2 gap-px bg-borde md:grid-cols-5 [&>*:last-child]:col-span-2 md:[&>*:last-child]:col-span-1">{children}</dl>;
}

export function PasoResultados({
  e,
  opciones,
  opcionesPpt,
  cantidadOpcionesPpt,
  alCambiar,
  alVolver,
  alNueva,
}: {
  e: Entradas;
  opciones: OpcionesFormulario;
  opcionesPpt: KitsOpcion[] | null;
  cantidadOpcionesPpt: number | null;
  alCambiar: (c: Partial<Entradas>) => void;
  alVolver: () => void;
  alNueva: () => void;
}) {
  const [calculo, setCalculo] = useState<{ para: Entradas; r: Resultado | null; error: string | null } | null>(null);
  const [errorExporte, setErrorExporte] = useState<string | null>(null);
  const calculando = calculo?.para !== e;
  const r = calculo?.r ?? null;
  const error = errorExporte ?? calculo?.error ?? null;
  const [exportando, setExportando] = useState(false);

  // Recalcula ante cualquier cambio (sensibilidad rápida), con una pequeña espera.
  useEffect(() => {
    let vigente = true;
    const t = setTimeout(() => {
      api
        .calcular(e)
        .then((res) => vigente && setCalculo({ para: e, r: res, error: null }))
        .catch((err: ErrorApi) => vigente && setCalculo((c) => ({ para: e, r: c?.r ?? null, error: err.message })));
    }, 250);
    return () => {
      vigente = false;
      clearTimeout(t);
    };
  }, [e]);

  const exportar = async () => {
    setExportando(true);
    setErrorExporte(null);
    try {
      await api.exportarExcel(e);
    } catch (err) {
      setErrorExporte((err as Error).message);
    } finally {
      setExportando(false);
    }
  };

  const puedeBaterias = e.tipo_inversor === "HIBRIDO" && e.baterias.modelo != null;

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-[-0.01em] text-tinta">{e.cliente || "Propuesta"}</h2>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-tinta-2">
            {describirKits(e.kit1, e.kit2)} · {e.instalacion} · {e.tipo_inversor}
            <span aria-live="polite" className={`inline-flex items-center gap-1.5 text-tenue transition-opacity duration-150 ${calculando ? "opacity-100" : "opacity-0"}`}>
              {calculando && (
                <>
                  <LoaderCircle aria-hidden className="size-3.5 animate-spin" />
                  recalculando…
                </>
              )}
            </span>
          </p>
        </div>
        <Boton variante="secundario" onClick={exportar} cargando={exportando} icono={<FileSpreadsheet aria-hidden />}>
          Descargar Excel
        </Boton>
      </div>

      {error && <Aviso nivel="error">{error}</Aviso>}

      {!r && !error && (
        <div aria-hidden className="h-52 animate-pulse rounded-xl border border-borde bg-superficie" />
      )}

      {r && (
        <>
          <div className={`overflow-hidden rounded-xl border border-borde transition-opacity duration-200 ${calculando ? "opacity-60" : ""}`}>
            <GrupoKpi>
              <Kpi destacado etiqueta="Inversión" valor={fmt.usd(r.inversion.total_usd)} />
              <Kpi destacado etiqueta="Ahorro anual" valor={fmt.usd(r.economia.ahorro_anual_usd)} detalle={`$ ${fmt.entero(r.economia.ahorro_anual_ars)}`} />
              <Kpi destacado etiqueta="ROI" valor={fmt.anios(r.roi_anios)} />
              <Kpi destacado etiqueta="TIR" valor={fmt.pct(r.van_tir.tir, 1)} detalle="a 25 años" />
              <Kpi
                destacado
                etiqueta="VAN"
                valor={fmt.usd(r.van_tir.van)}
                detalle={`${e.periodo_evaluacion} años al ${fmt.pct(e.tasa_descuento)}`}
              />
            </GrupoKpi>
            <div className="h-px bg-borde" />
            <GrupoKpi>
              <Kpi etiqueta="Potencia" valor={`${fmt.n(r.kwp_total, 2)} kWp`} />
              <Kpi etiqueta="Generación" valor={`${fmt.entero(r.energia.generacion_anual_kwh)} kWh`} detalle="por año" />
              <Kpi etiqueta="Cobertura" valor={fmt.pct(r.energia.cobertura)} detalle="del consumo anual" />
              <Kpi etiqueta="Autoconsumo" valor={fmt.pct(r.energia.autoconsumo_pct)} detalle="de lo generado" />
              <Kpi
                etiqueta="Superficie"
                valor={`${fmt.entero(r.superficie_m2)} m²`}
                detalle={e.m2_disponibles != null ? `de ${fmt.entero(e.m2_disponibles)} m² disponibles` : undefined}
              />
            </GrupoKpi>
          </div>

          {r.alertas.length > 0 && (
            <div className="space-y-2">
              {r.alertas.map((a) => (
                <Aviso key={a.codigo + a.mensaje} nivel={a.nivel}>
                  {a.mensaje}
                </Aviso>
              ))}
            </div>
          )}

          <Seccion titulo="Sensibilidad rápida">
            <div className="grid grid-cols-1 gap-x-4 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
              <Campo etiqueta="Valor del dólar">
                <Numero valor={e.dolar} sufijo="$/U$D" alCambiar={(v) => alCambiar({ dolar: v ?? 0 })} />
              </Campo>
              <Campo etiqueta="Tasa de descuento">
                <Numero valor={e.tasa_descuento} porcentaje alCambiar={(v) => alCambiar({ tasa_descuento: v ?? 0 })} />
              </Campo>
              <Campo etiqueta="Inhibición de inyección">
                <SiNo valor={e.inhibicion_inyeccion} alCambiar={(v) => alCambiar({ inhibicion_inyeccion: v })} />
              </Campo>
              <Campo etiqueta="Baterías" ayuda={puedeBaterias ? undefined : "Requiere sistema híbrido con modelo elegido"}>
                <SiNo
                  valor={e.baterias.incluye}
                  deshabilitado={!puedeBaterias}
                  alCambiar={(v) => alCambiar({ baterias: { ...e.baterias, incluye: v } })}
                />
              </Campo>
            </div>
          </Seccion>

          <div className="grid gap-6 lg:grid-cols-2">
            <GraficoMensual r={r} />
            <GraficoRoi r={r} />
            {e.financiacion.porcentaje > 0 && <GraficoFinanciacion r={r} />}
            <Seccion titulo="Impacto ambiental">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-5 text-sm">
                <div>
                  <dt className="text-[13px] text-tinta-2">CO₂ evitado por año</dt>
                  <dd className="mt-0.5 text-lg font-semibold tabular-nums">{fmt.n(r.huella.tco2_anio, 1)} t</dd>
                </div>
                <div>
                  <dt className="text-[13px] text-tinta-2">CO₂ evitado en 25 años</dt>
                  <dd className="mt-0.5 text-lg font-semibold tabular-nums">{fmt.entero(r.huella.tco2_25_anios)} t</dd>
                </div>
                <div>
                  <dt className="text-[13px] text-tinta-2">Equivale a árboles</dt>
                  <dd className="mt-0.5 text-lg font-semibold tabular-nums">{fmt.entero(r.huella.arboles)}</dd>
                </div>
                <div>
                  <dt className="text-[13px] text-tinta-2">Equivale a autos</dt>
                  <dd className="mt-0.5 text-lg font-semibold tabular-nums">{fmt.entero(r.huella.autos)}</dd>
                </div>
              </dl>
              {e.ppa.aplica && (
                <p className="mt-5 border-t border-borde pt-4 text-sm text-tinta-2">
                  PPA: TIR {fmt.pct(r.ppa.tir, 1)} a {e.ppa.periodo_contrato} años · ventas año 1 {fmt.usd(r.ppa.ventas_anio1_usd)}
                </p>
              )}
            </Seccion>
          </div>

          <SeccionPresentacion
            e={e}
            diapositivas={opciones.diapositivas}
            opcionesPpt={opcionesPpt}
            cantidadOpcionesPpt={cantidadOpcionesPpt}
          />
        </>
      )}

      <div className="flex-1" />
      <BarraAcciones>
        <Boton variante="secundario" onClick={alVolver} icono={<ArrowLeft aria-hidden />}>
          Volver a opciones
        </Boton>
        <Boton variante="fantasma" onClick={alNueva} icono={<FilePlus aria-hidden />}>
          Nueva propuesta
        </Boton>
      </BarraAcciones>
    </div>
  );
}
