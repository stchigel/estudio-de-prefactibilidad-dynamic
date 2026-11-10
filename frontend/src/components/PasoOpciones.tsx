"use client";

import { ArrowLeft, ChevronDown, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import { fmt } from "@/lib/estado";
import type { Entradas, Kit, KitsOpcion, Opcion, OpcionesFormulario, ResultadoBusqueda } from "@/lib/tipos";
import { Aviso, BarraAcciones, Boton, Campo, Grilla, Insignia, Numero, Opciones, Seccion, SiNo } from "./ui";

export function describirKits(k1: Kit, k2: Kit | null) {
  const parte = (k: Kit) => `${k.cantidad} × ${fmt.n(k.kwp, 2)} kWp`;
  return k2 && k2.cantidad > 0 ? `${parte(k1)} + ${parte(k2)}` : parte(k1);
}

/** Identifica una combinación de kits (la distancia al tablero no la distingue). */
const clave = (k1: Kit, k2: Kit | null) => `${k1.kwp}x${k1.cantidad}+${k2 && k2.cantidad > 0 ? `${k2.kwp}x${k2.cantidad}` : "-"}`;

type Fila = Opcion & { manual?: boolean };

const MOTIVOS: Record<string, string> = {
  potencia: "superan la potencia contratada",
  superficie: "no entran en los m² disponibles",
  desperdicio: "desperdician demasiada energía con inhibición",
  sin_ahorro: "no generan ahorro",
  cobertura: "superan el consumo anual",
};

export function PasoOpciones({
  e,
  opciones,
  alElegir,
  alVolver,
}: {
  e: Entradas;
  opciones: OpcionesFormulario;
  /** `opcionesPpt`: las opciones tildadas para la tabla del PowerPoint (null = todas las de la búsqueda). */
  alElegir: (kit1: Kit, kit2: Kit | null, opcionesPpt: KitsOpcion[] | null, cantidadPpt: number) => void;
  alVolver: () => void;
}) {
  const [busqueda, setBusqueda] = useState<ResultadoBusqueda | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agregadas, setAgregadas] = useState<Fila[]>([]);
  const [elegida, setElegida] = useState<string | null>(null);
  // Opciones fuera de la tabla del PowerPoint; la elegida siempre va.
  const [destildadas, setDestildadas] = useState<Set<string>>(new Set());
  const [manual, setManual] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const [errorAgregar, setErrorAgregar] = useState<string | null>(null);
  const [kit1, setKit1] = useState<Kit>(e.kit1);
  const [kit2, setKit2] = useState<Kit | null>(e.kit2);

  useEffect(() => {
    let vigente = true;
    api
      .buscarOpciones(e)
      .then((r) => {
        if (!vigente) return;
        setBusqueda(r);
        const rec = r.opciones.find((o) => o.recomendada) ?? r.opciones[0];
        if (rec) setElegida(clave(rec.kit1, rec.kit2));
      })
      .catch((err: ErrorApi) => vigente && setError(err.message));
    return () => {
      vigente = false;
    };
    // La búsqueda se hace una vez al entrar al paso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Las de la búsqueda y las agregadas a mano, juntas y ordenadas por potencia.
  const filas = useMemo<Fila[]>(
    () => [...(busqueda?.opciones ?? []), ...agregadas].sort((a, b) => a.resultado.kwp_total - b.resultado.kwp_total),
    [busqueda, agregadas],
  );

  const kwps = opciones.kits.map((k) => k.kwp);
  const enPpt = (f: Fila) => clave(f.kit1, f.kit2) === elegida || !destildadas.has(clave(f.kit1, f.kit2));
  const opcionesPpt = (): KitsOpcion[] | null => {
    if (destildadas.size === 0 && agregadas.length === 0) return null;
    return filas.filter(enPpt).map((f) => ({ kit1: f.kit1, kit2: f.kit2 }));
  };
  const alternar = (k: string) =>
    setDestildadas((previas) => {
      const nuevas = new Set(previas);
      if (!nuevas.delete(k)) nuevas.add(k);
      return nuevas;
    });

  const agregar = async () => {
    const k2 = kit2 && kit2.cantidad > 0 ? kit2 : null;
    const k = clave(kit1, k2);
    setErrorAgregar(null);
    if (filas.some((f) => clave(f.kit1, f.kit2) === k)) {
      setElegida(k); // ya está en la tabla: se la elige
      return;
    }
    setAgregando(true);
    try {
      const resultado = await api.calcular({ ...e, kit1, kit2: k2 });
      setAgregadas((previas) => [...previas, { kit1, kit2: k2, recomendada: false, resultado, manual: true }]);
      setElegida(k);
    } catch (err) {
      setErrorAgregar((err as ErrorApi).message);
    } finally {
      setAgregando(false);
    }
  };

  const verResultados = () => {
    const f = filas.find((x) => clave(x.kit1, x.kit2) === elegida);
    if (f) alElegir(f.kit1, f.kit2, opcionesPpt(), filas.filter(enPpt).length);
  };

  return (
    <div className="flex flex-1 flex-col gap-6">
      <Seccion titulo="Opciones propuestas">
        {!busqueda && !error && (
          <p className="flex items-center gap-2 py-6 text-sm text-tinta-2" role="status">
            <LoaderCircle aria-hidden className="size-4 animate-spin text-tenue" />
            Evaluando combinaciones de kits…
          </p>
        )}
        {error && <Aviso nivel="error">{error}</Aviso>}
        {busqueda && filas.length === 0 && (
          <Aviso nivel="advertencia">Ninguna combinación del catálogo cumple las restricciones. Agregá los kits a mano.</Aviso>
        )}
        {busqueda && filas.length > 0 && (
          <>
            <div className="-mx-5 -mt-5 overflow-x-auto">
              <table className="w-full min-w-[960px] text-sm tabular-nums">
                <thead>
                  <tr className="border-b border-borde bg-superficie-2 text-left text-xs text-tinta-2">
                    <th scope="col" className="py-2 pl-5 pr-2 font-medium">Elegir</th>
                    <th scope="col" className="px-2 font-medium">En el PPT</th>
                    <th scope="col" className="px-2 font-medium">Kits</th>
                    <th scope="col" className="px-2 text-right font-medium">Potencia</th>
                    <th scope="col" className="px-2 text-right font-medium">Cobertura</th>
                    <th scope="col" className="px-2 text-right font-medium">Autoconsumo</th>
                    <th scope="col" className="px-2 text-right font-medium">Inversión</th>
                    <th scope="col" className="px-2 text-right font-medium">Ahorro anual</th>
                    <th scope="col" className="px-2 text-right font-medium">ROI</th>
                    <th scope="col" className="px-2 text-right font-medium">TIR</th>
                    <th scope="col" className="pl-2 pr-5 text-right font-medium">Superficie</th>
                  </tr>
                </thead>
                <tbody>
                  {filas.map((o) => {
                    const r = o.resultado;
                    const k = clave(o.kit1, o.kit2);
                    const esElegida = k === elegida;
                    const fuera = !enPpt(o);
                    return (
                      <tr
                        key={k}
                        onClick={() => setElegida(k)}

                        className={`cursor-pointer border-b border-borde transition-colors duration-150 last:border-0 ${
                          esElegida ? "bg-acento-suave" : "hover:bg-superficie-2/70"
                        } ${fuera ? "text-tenue" : "text-tinta"}`}
                      >
                        <td className="py-2.5 pl-5 pr-2">
                          <input type="radio" checked={esElegida} onChange={() => setElegida(k)} aria-label={`Elegir ${describirKits(o.kit1, o.kit2)}`} />
                        </td>
                        <td className="px-2" onClick={(ev) => ev.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={!fuera}
                            disabled={esElegida}
                            onChange={() => alternar(k)}
                            aria-label={`Incluir ${describirKits(o.kit1, o.kit2)} en la tabla del PowerPoint`}
                            title={esElegida ? "La opción elegida siempre se incluye" : undefined}
                          />
                        </td>
                        <td className={`px-2 ${esElegida ? "font-medium" : ""}`}>
                          <span className="flex flex-wrap items-center gap-2">
                            {describirKits(o.kit1, o.kit2)}
                            {o.recomendada && <Insignia tono="bueno">Recomendada</Insignia>}
                            {o.manual && <Insignia tono="acento">Agregada a mano</Insignia>}
                            {fuera && <Insignia tono="neutro">Fuera del PPT</Insignia>}
                          </span>
                        </td>
                        <td className="px-2 text-right">{fmt.n(r.kwp_total, 2)} kWp</td>
                        <td className="px-2 text-right">{fmt.pct(r.energia.cobertura)}</td>
                        <td className="px-2 text-right">{fmt.pct(r.energia.autoconsumo_pct)}</td>
                        <td className="px-2 text-right">{fmt.usd(r.inversion.total_usd)}</td>
                        <td className="px-2 text-right">{fmt.usd(r.economia.ahorro_anual_usd)}</td>
                        <td className="px-2 text-right">{fmt.anios(r.roi_anios)}</td>
                        <td className="px-2 text-right">{fmt.pct(r.van_tir.tir, 1)}</td>
                        <td className="pl-2 pr-5 text-right">{fmt.entero(r.superficie_m2)} m²</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 max-w-[90ch] space-y-1 text-xs leading-5 text-tinta-2">
              <p>
                Se muestra la recomendada, dos tamaños más chicos y dos más grandes. La recomendada es la de mejor ROI; ante diferencias
                menores a 0,2 años se prefiere la de mayor cobertura, pero se muestran las dos combinaciones. Se evaluaron{" "}
                {fmt.entero(busqueda.evaluadas)} combinaciones, {fmt.entero(busqueda.validas)} válidas.
              </p>
              <p>Las opciones tildadas en «En el PPT» forman la tabla de opciones de la presentación; las destildadas se ven atenuadas.</p>
              {Object.entries(busqueda.descartes).map(([motivo, n]) => (
                <p key={motivo}>
                  {fmt.entero(n)} descartadas porque {MOTIVOS[motivo] ?? motivo}.
                </p>
              ))}
            </div>
            {busqueda.limitado_por_potencia && (
              <div className="mt-3">
                <Aviso nivel="info">El tamaño está limitado por la potencia contratada: con más potencia habría opciones de mejor retorno.</Aviso>
              </div>
            )}
          </>
        )}
      </Seccion>

      <Seccion
        titulo="Agregar kits a mano"
        accion={
          <Boton
            variante="fantasma"
            onClick={() => setManual(!manual)}
            icono={<ChevronDown aria-hidden className={`transition-transform duration-150 ${manual ? "rotate-180" : ""}`} />}
          >
            {manual ? "Ocultar" : "Mostrar"}
          </Boton>
        }
      >
        {manual ? (
          <div className="space-y-4">
            <Grilla>
              <Campo etiqueta="Kit 1">
                <Opciones valor={kit1.kwp} opciones={kwps} etiquetas={(v) => `${fmt.n(v, 2)} kWp`} alCambiar={(v) => setKit1({ ...kit1, kwp: v })} />
              </Campo>
              <Campo etiqueta="Cantidad kit 1">
                <Numero valor={kit1.cantidad} alCambiar={(v) => setKit1({ ...kit1, cantidad: Math.round(v ?? 0) })} />
              </Campo>
              <Campo etiqueta="Distancia inversor–TGBT kit 1" ayuda="Los primeros 5 m están incluidos">
                <Numero valor={kit1.distancia_tgbt_m} sufijo="m" alCambiar={(v) => setKit1({ ...kit1, distancia_tgbt_m: v ?? 0 })} />
              </Campo>
              <Campo etiqueta="Segundo kit">
                <SiNo valor={kit2 != null} alCambiar={(v) => setKit2(v ? { kwp: kwps[0], cantidad: 1, distancia_tgbt_m: 0 } : null)} />
              </Campo>
              {kit2 && (
                <>
                  <Campo etiqueta="Kit 2">
                    <Opciones valor={kit2.kwp} opciones={kwps} etiquetas={(v) => `${fmt.n(v, 2)} kWp`} alCambiar={(v) => setKit2({ ...kit2, kwp: v })} />
                  </Campo>
                  <Campo etiqueta="Cantidad kit 2">
                    <Numero valor={kit2.cantidad} alCambiar={(v) => setKit2({ ...kit2, cantidad: Math.round(v ?? 0) })} />
                  </Campo>
                  <Campo etiqueta="Distancia inversor–TGBT kit 2">
                    <Numero valor={kit2.distancia_tgbt_m} sufijo="m" alCambiar={(v) => setKit2({ ...kit2, distancia_tgbt_m: v ?? 0 })} />
                  </Campo>
                </>
              )}
            </Grilla>
            {errorAgregar && <Aviso nivel="error">{errorAgregar}</Aviso>}
            <div className="flex flex-wrap items-center justify-end gap-3">
              <span className="text-xs text-tenue">Se suma a la tabla de arriba y queda elegida; después se puede cambiar.</span>
              <Boton variante="secundario" onClick={agregar} deshabilitado={kit1.cantidad < 1} cargando={agregando} icono={<Plus aria-hidden />}>
                Agregar a la tabla
              </Boton>
            </div>
          </div>
        ) : (
          <p className="text-sm text-tinta-2">Para sumar a la tabla otra combinación de kits del catálogo, o fijar la distancia al tablero.</p>
        )}
      </Seccion>

      <div className="flex-1" />
      <BarraAcciones>
        <Boton variante="secundario" onClick={alVolver} icono={<ArrowLeft aria-hidden />}>
          Volver
        </Boton>
        <Boton onClick={verResultados} deshabilitado={!elegida || filas.length === 0}>
          Ver resultados
        </Boton>
      </BarraAcciones>
    </div>
  );
}
