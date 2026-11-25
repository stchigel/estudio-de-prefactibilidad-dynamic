"use client";

import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import type { Alerta, Entradas, OpcionesFormulario, Sugerencias } from "@/lib/tipos";
import { Aviso, BarraAcciones, Boton, Campo, claseInput, Grilla, Numero, Opciones, Seccion, SiNo, Texto } from "./ui";

type Actualizar = (cambios: Partial<Entradas>) => void;

type IdSeccion = "propuesta" | "costos" | "sistema" | "baterias" | "ajustes" | "financiacion" | "ppa";

/** Sección del formulario a la que pertenece el campo de una alerta de validación. */
function seccionDe(campo: string | null | undefined): IdSeccion | null {
  if (!campo) return null;
  if (campo.startsWith("baterias")) return "baterias";
  if (campo.startsWith("financiacion")) return "financiacion";
  if (campo.startsWith("ppa")) return "ppa";
  if (campo.startsWith("capacitores")) return "sistema";
  if (/^(costo_|tasa_mayorista|tasa_cammesa|tasa_976|tasas_mun_prov|res281|retribucion|potencia_contratada_cammesa)/.test(campo)) return "costos";
  if (/^(tipo_inversor|inhibicion|banco_capacitores|instalacion|acimut|inclinacion|inversor)/.test(campo)) return "sistema";
  if (/^(k_incertidumbre|comision|tasa_descuento|periodo_evaluacion)/.test(campo)) return "ajustes";
  return "propuesta";
}

function irA(id: string) {
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(id)?.scrollIntoView({ behavior: reducido ? "auto" : "smooth", block: "start" });
}

/** Sección visible: la última cuyo título ya pasó por debajo de la barra superior. */
function useSeccionActiva(ids: string[]) {
  const [activa, setActiva] = useState(ids[0]);
  const clave = ids.join(",");
  useEffect(() => {
    const lista = clave.split(",");
    let cuadro = 0;
    const medir = () => {
      cuadro = 0;
      const limite = window.innerHeight * 0.35;
      let actual = lista[0];
      for (const id of lista) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= limite) actual = id;
      }
      // Al llegar al final, la última sección queda activa aunque sea corta.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) actual = lista[lista.length - 1];
      setActiva(actual);
    };
    const alMover = () => {
      if (!cuadro) cuadro = requestAnimationFrame(medir);
    };
    medir();
    window.addEventListener("scroll", alMover, { passive: true });
    window.addEventListener("resize", alMover);
    return () => {
      window.removeEventListener("scroll", alMover);
      window.removeEventListener("resize", alMover);
      if (cuadro) cancelAnimationFrame(cuadro);
    };
  }, [clave]);
  return activa;
}

function IndiceSecciones({
  secciones,
  activa,
  errores,
}: {
  secciones: { id: IdSeccion; titulo: string; estado?: string }[];
  activa: string;
  errores: Partial<Record<IdSeccion, number>>;
}) {
  return (
    <nav aria-label="Secciones del proyecto" className="hidden lg:block">
      <ul className="sticky top-[7.5rem] flex flex-col gap-0.5 xl:top-20">
        {secciones.map(({ id, titulo, estado }) => {
          const esActiva = id === activa;
          const n = errores[id] ?? 0;
          return (
            <li key={id}>
              <a
                href={`#${id}`}
                onClick={(ev) => {
                  ev.preventDefault();
                  irA(id);
                  history.replaceState(null, "", `#${id}`);
                }}
                aria-current={esActiva ? "location" : undefined}
                className={`flex items-start justify-between gap-2 rounded-md px-3 py-1.5 text-sm transition-colors duration-150 ${
                  esActiva ? "bg-superficie font-medium text-tinta ring-1 ring-borde" : "text-tinta-2 hover:bg-superficie-2 hover:text-tinta"
                }`}
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate">{titulo}</span>
                  {estado && <span className="truncate text-xs font-normal text-tenue">{estado}</span>}
                </span>
                {n > 0 && (
                  <span
                    className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-critico px-1.5 text-[11px] font-semibold tabular-nums text-white"
                    aria-label={`${n} ${n === 1 ? "error" : "errores"}`}
                  >
                    {n}
                  </span>
                )}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function PasoProyecto({
  e,
  opciones,
  sugerencias,
  alCambiar,
  alContinuar,
  alVolver,
}: {
  e: Entradas;
  opciones: OpcionesFormulario;
  sugerencias: Sugerencias | null;
  alCambiar: Actualizar;
  alContinuar: () => void;
  alVolver: () => void;
}) {
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [validando, setValidando] = useState(false);
  const [errorRed, setErrorRed] = useState<string | null>(null);
  const error = (campo: string) => alertas.find((a) => a.campo === campo && a.nivel === "error")?.mensaje;
  const b = e.baterias;
  const hibrido = e.tipo_inversor === "HIBRIDO";
  const bateria = opciones.baterias.find((x) => x.modelo === b.modelo);

  const setBaterias = async (cambios: Partial<Entradas["baterias"]>) => {
    const nuevas = { ...b, ...cambios };
    alCambiar({ baterias: nuevas, ...(cambios.incluye ? { inversor: "Deye Hib" } : {}) });
    if (nuevas.modelo && ("modelo" in cambios || "cantidad" in cambios)) {
      try {
        const s = await api.sugerirBaterias(nuevas.modelo, nuevas.cantidad);
        alCambiar({ baterias: { ...nuevas, ...s } });
      } catch {
        /* la sugerencia es opcional */
      }
    }
  };

  const continuar = async () => {
    setValidando(true);
    setErrorRed(null);
    try {
      const lista = await api.validar(e);
      // Los kits los define la búsqueda de opciones: sus errores no frenan este paso.
      const relevantes = lista.filter((a) => !a.campo?.startsWith("kit"));
      setAlertas(relevantes);
      const primera = relevantes.find((a) => a.nivel === "error");
      if (!primera) alContinuar();
      else requestAnimationFrame(() => irA(seccionDe(primera.campo) ?? "propuesta"));
    } catch (err) {
      setErrorRed((err as ErrorApi).message ?? "No se pudo validar");
    } finally {
      setValidando(false);
    }
  };

  const errores: Partial<Record<IdSeccion, number>> = {};
  for (const a of alertas) {
    const id = a.nivel === "error" ? seccionDe(a.campo) : null;
    if (id) errores[id] = (errores[id] ?? 0) + 1;
  }
  const secciones: { id: IdSeccion; titulo: string; estado?: string }[] = [
    { id: "propuesta", titulo: "Propuesta y cliente", estado: e.cliente || undefined },
    { id: "costos", titulo: "Costos de energía" },
    { id: "sistema", titulo: "Sistema", estado: `${e.tipo_inversor} · ${e.instalacion}` },
    ...(hibrido ? [{ id: "baterias" as const, titulo: "Baterías", estado: b.incluye ? (b.modelo ?? "Sin modelo") : "No incluye" }] : []),
    { id: "ajustes", titulo: "Ajustes y evaluación" },
    {
      id: "financiacion",
      titulo: "Financiación",
      estado: e.financiacion.porcentaje > 0 ? `${Number((e.financiacion.porcentaje * 100).toFixed(2)).toString().replace(".", ",")} % a financiar` : "Sin financiación",
    },
    { id: "ppa", titulo: "PPA", estado: e.ppa.aplica ? `${e.ppa.periodo_contrato} años` : "No aplica" },
  ];
  const activa = useSeccionActiva(secciones.map((x) => x.id));

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
        <IndiceSecciones secciones={secciones} activa={activa} errores={errores} />
        <div className="flex min-w-0 flex-col gap-6">
      <Seccion id="propuesta" titulo="Propuesta y cliente">
        <Grilla>
          <Campo etiqueta="N° de propuesta">
            <Numero valor={e.numero_propuesta} vacioEsNulo alCambiar={(v) => alCambiar({ numero_propuesta: v })} />
          </Campo>
          <Campo etiqueta="Fecha">
            <input
              type="date"
              className={claseInput}
              value={e.fecha ?? ""}
              onChange={(ev) => alCambiar({ fecha: ev.target.value || null })}
            />
          </Campo>
          <Campo etiqueta="Valor del dólar" error={error("dolar")}>
            <Numero valor={e.dolar} sufijo="$/U$D" alCambiar={(v) => alCambiar({ dolar: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Cliente">
            <Texto valor={e.cliente} alCambiar={(v) => alCambiar({ cliente: v })} />
          </Campo>
          <Campo etiqueta="Provincia" error={error("provincia")}>
            <Opciones valor={e.provincia} opciones={opciones.provincias} alCambiar={(v) => alCambiar({ provincia: v })} />
          </Campo>
          <Campo etiqueta="Categoría">
            <Opciones valor={e.categoria} opciones={opciones.categorias} alCambiar={(v) => alCambiar({ categoria: v })} />
          </Campo>
          <Campo etiqueta="Distribuidora">
            <Texto valor={e.distribuidora} alCambiar={(v) => alCambiar({ distribuidora: v })} />
          </Campo>
          <Campo etiqueta="Tarifa">
            <Texto valor={e.tarifa} alCambiar={(v) => alCambiar({ tarifa: v })} />
          </Campo>
          <Campo etiqueta="Potencia contratada" ayuda="De la factura se toma la mayor (pico / fuera de pico)">
            <Numero valor={e.potencia_contratada_kw} sufijo="kW" alCambiar={(v) => alCambiar({ potencia_contratada_kw: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Horario de trabajo">
            <Opciones valor={e.horario_trabajo} opciones={opciones.horarios} alCambiar={(v) => alCambiar({ horario_trabajo: v })} />
          </Campo>
          <Campo etiqueta="Horas por día" error={error("horas_por_dia")}>
            <Opciones valor={e.horas_por_dia} opciones={opciones.horas_por_dia} alCambiar={(v) => alCambiar({ horas_por_dia: v })} />
          </Campo>
          <Campo etiqueta="m² disponibles" ayuda="Vacío si no se conoce">
            <Numero valor={e.m2_disponibles} vacioEsNulo sufijo="m²" alCambiar={(v) => alCambiar({ m2_disponibles: v })} />
          </Campo>
          {e.m2_disponibles != null && (
            <Campo etiqueta="Origen de los m²">
              <Opciones valor={e.origen_m2} opciones={opciones.origenes_superficie} alCambiar={(v) => alCambiar({ origen_m2: v })} />
            </Campo>
          )}
        </Grilla>
      </Seccion>

      <Seccion id="costos" titulo="Costos de energía">
        <Grilla>
          <Campo etiqueta="Costo mayorista">
            <Numero valor={e.costo_mayorista} sufijo="$/kWh" alCambiar={(v) => alCambiar({ costo_mayorista: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Tasas mayorista">
            <Numero valor={e.tasa_mayorista} porcentaje alCambiar={(v) => alCambiar({ tasa_mayorista: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Costo CAMMESA">
            <Numero valor={e.costo_cammesa} sufijo="$/kWh" alCambiar={(v) => alCambiar({ costo_cammesa: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Tasas CAMMESA">
            <Numero valor={e.tasa_cammesa} porcentaje alCambiar={(v) => alCambiar({ tasa_cammesa: v ?? 0 })} />
          </Campo>
          <Campo
            etiqueta="Costo distribuidora"
            ayuda={
              sugerencias?.costo_distribuidora_origen === "resto"
                ? "Precio del kWh en resto de la factura (no el monómico)"
                : sugerencias?.costo_distribuidora_origen === "energia_activa"
                  ? "Energía activa / kWh: la factura no trae el precio en resto. Revisar"
                  : "Precio del kWh en resto (no el monómico)"
            }
          >
            <Numero valor={e.costo_distribuidora} sufijo="$/kWh" alCambiar={(v) => alCambiar({ costo_distribuidora: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Tasas municipales / provinciales">
            <Numero valor={e.tasas_mun_prov} porcentaje alCambiar={(v) => alCambiar({ tasas_mun_prov: v ?? 0 })} />
          </Campo>
          {e.categoria === "GUDI" && (
            <Campo etiqueta="Tasa Res. 976/23 promedio">
              <Numero valor={e.tasa_976} porcentaje alCambiar={(v) => alCambiar({ tasa_976: v ?? 0 })} />
            </Campo>
          )}
          <Campo etiqueta="Res. 976/281">
            <Numero valor={e.res281_usd_mwh} sufijo="U$D/MWh" alCambiar={(v) => alCambiar({ res281_usd_mwh: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Retribución por inyección">
            <Numero valor={e.retribucion_inyeccion} sufijo="$/kWh" alCambiar={(v) => alCambiar({ retribucion_inyeccion: v ?? 0 })} />
          </Campo>
        </Grilla>
      </Seccion>

      <Seccion id="sistema" titulo="Sistema">
        <Grilla>
          <Campo etiqueta="Tipo de inversor">
            <Opciones
              valor={e.tipo_inversor}
              opciones={opciones.tipos_inversor}
              alCambiar={(v) => alCambiar({ tipo_inversor: v, ...(v === "ON GRID" ? { baterias: { ...b, incluye: false } } : {}) })}
            />
          </Campo>
          <Campo etiqueta="Inhibición de inyección">
            <SiNo valor={e.inhibicion_inyeccion} alCambiar={(v) => alCambiar({ inhibicion_inyeccion: v })} />
          </Campo>
          <Campo etiqueta="Banco de capacitores">
            <SiNo valor={e.banco_capacitores} alCambiar={(v) => alCambiar({ banco_capacitores: v })} />
          </Campo>
          <Campo etiqueta="Tipo de instalación">
            <Opciones valor={e.instalacion} opciones={opciones.instalaciones} alCambiar={(v) => alCambiar({ instalacion: v })} />
          </Campo>
          <Campo etiqueta="Acimut" error={error("acimut")}>
            <Opciones valor={e.acimut} opciones={opciones.acimuts} etiquetas={(v) => `${v}°`} alCambiar={(v) => alCambiar({ acimut: v })} />
          </Campo>
          <Campo etiqueta="Inclinación" error={error("inclinacion")}>
            <Opciones
              valor={e.inclinacion}
              opciones={opciones.inclinaciones}
              etiquetas={(v) => `${v}°`}
              alCambiar={(v) => alCambiar({ inclinacion: v })}
            />
          </Campo>
          <Campo etiqueta="Inversor" error={error("inversor")}>
            <Opciones
              valor={e.inversor}
              opciones={opciones.inversores}
              deshabilitado={b.incluye}
              alCambiar={(v) => alCambiar({ inversor: v })}
            />
          </Campo>
        </Grilla>
        {e.banco_capacitores && (
          <div className="mt-5 border-t border-borde pt-5">
            {sugerencias?.cargo_factor_potencia && (
              <div className="mb-4">
                <Aviso nivel="info">
                  La factura cobra cargo por factor de potencia: se recomienda banco de capacitores
                  {sugerencias.kvar_sugeridos != null && ` (${sugerencias.kvar_sugeridos} kVAr para llegar a cos φ 0,95)`}. Completar
                  inversión y ahorro.
                </Aviso>
              </div>
            )}
            <Grilla>
              <Campo etiqueta="Capacitores">
                <Numero valor={e.capacitores.kvar} sufijo="kVAr" alCambiar={(v) => alCambiar({ capacitores: { ...e.capacitores, kvar: v ?? 0 } })} />
              </Campo>
              <Campo etiqueta="Inversión capacitores">
                <Numero
                  valor={e.capacitores.inversion_usd}
                  sufijo="U$D"
                  alCambiar={(v) => alCambiar({ capacitores: { ...e.capacitores, inversion_usd: v ?? 0 } })}
                />
              </Campo>
              <Campo etiqueta="Ahorro por capacitores">
                <Numero
                  valor={e.capacitores.ahorro_ars_anio}
                  sufijo="$/año"
                  alCambiar={(v) => alCambiar({ capacitores: { ...e.capacitores, ahorro_ars_anio: v ?? 0 } })}
                />
              </Campo>
            </Grilla>
          </div>
        )}
      </Seccion>

      {hibrido && (
        <Seccion id="baterias" titulo="Baterías">
          <Grilla>
            <Campo etiqueta="Incluye baterías" ayuda={b.incluye ? "Requiere inversor Deye Hib" : undefined}>
              <SiNo valor={b.incluye} alCambiar={(v) => setBaterias({ incluye: v })} />
            </Campo>
            {b.incluye && (
              <>
                <Campo etiqueta="Objetivo">
                  <Opciones valor={b.objetivo} opciones={opciones.objetivos_baterias} alCambiar={(v) => setBaterias({ objetivo: v })} />
                </Campo>
                {b.objetivo === "Cortes" && (
                  <Campo etiqueta="Autonomía">
                    <Numero valor={b.autonomia_h} sufijo="h" alCambiar={(v) => setBaterias({ autonomia_h: v ?? 0 })} />
                  </Campo>
                )}
                <Campo etiqueta="Modelo" error={error("baterias.modelo")} ancho={2}>
                  <Opciones
                    valor={b.modelo}
                    opciones={opciones.baterias.map((x) => x.modelo)}
                    alCambiar={(v) => setBaterias({ modelo: v })}
                  />
                </Campo>
                <Campo
                  etiqueta="Cantidad de baterías"
                  error={error("baterias.cantidad")}
                  ayuda={bateria ? `Mín ${bateria.min_baterias ?? "—"} · máx ${bateria.max_baterias ?? "—"}` : undefined}
                >
                  <Numero valor={b.cantidad} alCambiar={(v) => setBaterias({ cantidad: Math.round(v ?? 0) })} />
                </Campo>
                <Campo etiqueta="PDU" ayuda="Sugerido según el modelo">
                  <Numero valor={b.cantidad_pdu} alCambiar={(v) => alCambiar({ baterias: { ...b, cantidad_pdu: Math.round(v ?? 0) } })} />
                </Campo>
                <Campo etiqueta="Rack">
                  <Numero valor={b.cantidad_rack} alCambiar={(v) => alCambiar({ baterias: { ...b, cantidad_rack: Math.round(v ?? 0) } })} />
                </Campo>
              </>
            )}
          </Grilla>
        </Seccion>
      )}

      <Seccion id="ajustes" titulo="Ajustes y evaluación">
        <Grilla>
          <Campo etiqueta="K incertidumbre">
            <Numero valor={e.k_incertidumbre} porcentaje alCambiar={(v) => alCambiar({ k_incertidumbre: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Comisión / gastos" error={error("comision")}>
            <Numero valor={e.comision} porcentaje alCambiar={(v) => alCambiar({ comision: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Tasa de descuento">
            <Numero valor={e.tasa_descuento} porcentaje alCambiar={(v) => alCambiar({ tasa_descuento: v ?? 0 })} />
          </Campo>
          <Campo etiqueta="Período de evaluación">
            <Opciones
              valor={e.periodo_evaluacion}
              opciones={opciones.periodos_evaluacion}
              etiquetas={(v) => `${v} años`}
              alCambiar={(v) => alCambiar({ periodo_evaluacion: v })}
            />
          </Campo>
        </Grilla>
      </Seccion>

      <Seccion id="financiacion" titulo="Financiación">
        <Grilla>
          <Campo etiqueta="% a financiar">
            <Numero valor={e.financiacion.porcentaje} porcentaje alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, porcentaje: v ?? 0 } })} />
          </Campo>
          {e.financiacion.porcentaje > 0 && (
            <>
              <Campo etiqueta="Tipo">
                <Opciones
                  valor={e.financiacion.tipo}
                  opciones={opciones.tipos_financiacion}
                  etiquetas={(v) => (v === "Prestamo" ? "Préstamo" : v)}
                  alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, tipo: v } })}
                />
              </Campo>
              <Campo etiqueta="Moneda">
                <Opciones valor={e.financiacion.moneda} opciones={opciones.monedas} alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, moneda: v } })} />
              </Campo>
              <Campo
                etiqueta="Plazo total"
                error={error("financiacion.plazo_anios")}
                ayuda={
                  e.financiacion.gracia_anios > 0 && e.financiacion.plazo_anios > e.financiacion.gracia_anios
                    ? `${e.financiacion.plazo_anios - e.financiacion.gracia_anios} años de capital más intereses y ${e.financiacion.gracia_anios} de gracia (solo intereses)`
                    : "Incluye los años de gracia"
                }
              >
                <Numero
                  valor={e.financiacion.plazo_anios}
                  sufijo="años"
                  alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, plazo_anios: Math.round(v ?? 0) } })}
                />
              </Campo>
              <Campo etiqueta="Período de gracia">
                <Numero
                  valor={e.financiacion.gracia_anios}
                  sufijo="años"
                  alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, gracia_anios: Math.round(v ?? 0) } })}
                />
              </Campo>
              <Campo etiqueta="Tasa">
                <Numero valor={e.financiacion.tasa} porcentaje alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, tasa: v ?? 0 } })} />
              </Campo>
              <Campo etiqueta="Gastos administrativos">
                <Numero valor={e.financiacion.gastos_adm} porcentaje alCambiar={(v) => alCambiar({ financiacion: { ...e.financiacion, gastos_adm: v ?? 0 } })} />
              </Campo>
            </>
          )}
        </Grilla>
      </Seccion>

      <Seccion id="ppa" titulo="PPA">
        <Grilla>
          <Campo etiqueta="Aplica PPA">
            <SiNo valor={e.ppa.aplica} alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, aplica: v } })} />
          </Campo>
          {e.ppa.aplica && (
            <>
              <Campo etiqueta="Período del contrato">
                <Opciones
                  valor={e.ppa.periodo_contrato}
                  opciones={opciones.periodos_evaluacion}
                  etiquetas={(v) => `${v} años`}
                  alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, periodo_contrato: v } })}
                />
              </Campo>
              <Campo etiqueta="Precio de venta">
                <Numero valor={e.ppa.precio_usd_mwh} sufijo="U$D/MWh" alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, precio_usd_mwh: v ?? 0 } })} />
              </Campo>
              <Campo etiqueta="Inflación anual U$D">
                <Numero valor={e.ppa.inflacion_usd} porcentaje alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, inflacion_usd: v ?? 0 } })} />
              </Campo>
              <Campo etiqueta="Fee de salida" ayuda="Solo se aplica con períodos de 5 a 10 años (igual que la planilla)">
                <Numero valor={e.ppa.fee_salida_usd} sufijo="U$D" alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, fee_salida_usd: v ?? 0 } })} />
              </Campo>
              <Campo etiqueta="OE&M">
                <Numero valor={e.ppa.oem} porcentaje alCambiar={(v) => alCambiar({ ppa: { ...e.ppa, oem: v ?? 0 } })} />
              </Campo>
            </>
          )}
        </Grilla>
      </Seccion>

      {alertas.length > 0 && (
        <div className="space-y-2">
          {alertas.map((a) => (
            <Aviso key={a.codigo + a.mensaje} nivel={a.nivel}>
              {a.mensaje}
            </Aviso>
          ))}
        </div>
      )}
      {errorRed && <Aviso nivel="error">{errorRed}</Aviso>}
        </div>
      </div>

      <BarraAcciones>
        <Boton variante="secundario" onClick={alVolver} icono={<ArrowLeft aria-hidden />}>
          Volver
        </Boton>
        <Boton onClick={continuar} cargando={validando}>
          Buscar opciones
        </Boton>
      </BarraAcciones>
    </div>
  );
}
