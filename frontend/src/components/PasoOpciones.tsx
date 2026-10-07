"use client";

import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import { fmt } from "@/lib/estado";
import type { Entradas, Kit, OpcionesFormulario, ResultadoBusqueda } from "@/lib/tipos";
import { Aviso, Boton, Campo, Grilla, Insignia, Numero, Opciones, Seccion, SiNo } from "./ui";

export function describirKits(k1: Kit, k2: Kit | null) {
  const parte = (k: Kit) => `${k.cantidad} × ${fmt.n(k.kwp, 2)} kWp`;
  return k2 && k2.cantidad > 0 ? `${parte(k1)} + ${parte(k2)}` : parte(k1);
}

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
  alElegir: (kit1: Kit, kit2: Kit | null) => void;
  alVolver: () => void;
}) {
  const [busqueda, setBusqueda] = useState<ResultadoBusqueda | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elegida, setElegida] = useState(0);
  const [manual, setManual] = useState(false);
  const [kit1, setKit1] = useState<Kit>(e.kit1);
  const [kit2, setKit2] = useState<Kit | null>(e.kit2);

  useEffect(() => {
    let vigente = true;
    api
      .buscarOpciones(e)
      .then((r) => {
        if (!vigente) return;
        setBusqueda(r);
        setElegida(Math.max(0, r.opciones.findIndex((o) => o.recomendada)));
      })
      .catch((err: ErrorApi) => vigente && setError(err.message));
    return () => {
      vigente = false;
    };
    // La búsqueda se hace una vez al entrar al paso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const kwps = opciones.kits.map((k) => k.kwp);

  return (
    <div className="space-y-6">
      <Seccion titulo="Opciones propuestas">
        {!busqueda && !error && <p className="text-sm text-tinta-2">Evaluando combinaciones de kits…</p>}
        {error && <Aviso nivel="error">{error}</Aviso>}
        {busqueda && busqueda.opciones.length === 0 && (
          <Aviso nivel="advertencia">Ninguna combinación del catálogo cumple las restricciones. Elegí los kits a mano.</Aviso>
        )}
        {busqueda && busqueda.opciones.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm tabular-nums">
                <thead>
                  <tr className="border-b border-borde text-left text-xs text-tenue">
                    <th className="py-2 pr-2" />
                    <th className="px-2 font-medium">Kits</th>
                    <th className="px-2 text-right font-medium">Potencia</th>
                    <th className="px-2 text-right font-medium">Cobertura</th>
                    <th className="px-2 text-right font-medium">Autoconsumo</th>
                    <th className="px-2 text-right font-medium">Inversión</th>
                    <th className="px-2 text-right font-medium">Ahorro anual</th>
                    <th className="px-2 text-right font-medium">ROI</th>
                    <th className="px-2 text-right font-medium">TIR</th>
                    <th className="pl-2 text-right font-medium">Superficie</th>
                  </tr>
                </thead>
                <tbody>
                  {busqueda.opciones.map((o, i) => {
                    const r = o.resultado;
                    return (
                      <tr
                        key={i}
                        onClick={() => setElegida(i)}
                        className={`cursor-pointer border-b border-borde/60 last:border-0 ${i === elegida ? "bg-acento/10" : "hover:bg-plano"}`}
                      >
                        <td className="py-2 pr-2">
                          <input type="radio" checked={i === elegida} onChange={() => setElegida(i)} aria-label={`Opción ${i + 1}`} />
                        </td>
                        <td className="px-2">
                          <span className="flex flex-wrap items-center gap-2">
                            {describirKits(o.kit1, o.kit2)}
                            {o.recomendada && <Insignia tono="bueno">Recomendada</Insignia>}
                          </span>
                        </td>
                        <td className="px-2 text-right">{fmt.n(r.kwp_total, 2)} kWp</td>
                        <td className="px-2 text-right">{fmt.pct(r.energia.cobertura)}</td>
                        <td className="px-2 text-right">{fmt.pct(r.energia.autoconsumo_pct)}</td>
                        <td className="px-2 text-right">{fmt.usd(r.inversion.total_usd)}</td>
                        <td className="px-2 text-right">{fmt.usd(r.economia.ahorro_anual_usd)}</td>
                        <td className="px-2 text-right">{fmt.anios(r.roi_anios)}</td>
                        <td className="px-2 text-right">{fmt.pct(r.van_tir.tir, 1)}</td>
                        <td className="pl-2 text-right">{fmt.entero(r.superficie_m2)} m²</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 space-y-1 text-xs text-tinta-2">
              <p>
                La recomendada es la de mejor ROI; ante diferencias menores a 0,2 años se prefiere la de mayor cobertura. Se evaluaron{" "}
                {fmt.entero(busqueda.evaluadas)} combinaciones, {fmt.entero(busqueda.validas)} válidas.
              </p>
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
        titulo="Elegir kits a mano"
        accion={
          <Boton variante="fantasma" onClick={() => setManual(!manual)}>
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
            <div className="flex justify-end">
              <Boton variante="secundario" onClick={() => alElegir(kit1, kit2)} deshabilitado={kit1.cantidad < 1}>
                Calcular con estos kits
              </Boton>
            </div>
          </div>
        ) : (
          <p className="text-sm text-tinta-2">Para comparar otra combinación de kits del catálogo, o fijar la distancia al tablero.</p>
        )}
      </Seccion>

      <div className="flex justify-between">
        <Boton variante="secundario" onClick={alVolver}>
          Volver
        </Boton>
        <Boton
          onClick={() => {
            const o = busqueda?.opciones[elegida];
            if (o) alElegir(o.kit1, o.kit2);
          }}
          deshabilitado={!busqueda?.opciones.length}
        >
          Ver resultados
        </Boton>
      </div>
    </div>
  );
}
