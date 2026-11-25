"use client";

import { ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fmt, MESES } from "@/lib/estado";
import type { CampoConfianza, ConsumoMensual, OrigenConsumo, RespuestaExtraccion } from "@/lib/tipos";
import { Aviso, BarraAcciones, Boton, Insignia, Numero, Seccion, Selector } from "./ui";

const UMBRAL = 0.7;

const TONO_ORIGEN: Record<OrigenConsumo, "acento" | "neutro" | "advertencia" | "bueno"> = {
  factura: "bueno",
  historial: "acento",
  estimado: "advertencia",
  manual: "neutro",
};

const CAMPOS: [string, string][] = [
  ["distribuidora", "Distribuidora"],
  ["cliente_razon_social", "Cliente"],
  ["cliente_cuit", "CUIT"],
  ["provincia", "Provincia"],
  ["tarifa", "Tarifa"],
  ["periodo_mes", "Mes"],
  ["periodo_anio", "Año"],
  ["potencia_contratada_pico_kw", "Pot. contratada pico kW"],
  ["potencia_contratada_fuera_pico_kw", "Pot. contratada fuera pico kW"],
  ["kwh_total", "kWh total"],
  ["importe_basico_energia", "Importe básico $"],
  ["importe_energia_activa", "Importe energía activa $"],
  ["energia_reactiva_kvarh", "Energía reactiva kVArh"],
];

const FRANJAS = { valle: "Valle", resto: "Resto", pico: "Pico" } as const;

const ETIQUETA_ORIGEN: Record<OrigenConsumo, string> = { factura: "factura", historial: "historial", estimado: "estimado", manual: "manual" };

/** Resumen de la tabla: los mismos datos, totalizados para revisarlos de un vistazo. */
function ResumenConsumos({ consumos }: { consumos: ConsumoMensual[] }) {
  const totales = consumos.map((c) => c.valle + c.resto + c.pico);
  const total = totales.reduce((a, b) => a + b, 0);
  const conDatos = totales.map((t, i) => ({ t, mes: MESES[i] })).filter((x) => x.t > 0);
  const mayor = conDatos.reduce<(typeof conDatos)[number] | null>((m, x) => (!m || x.t > m.t ? x : m), null);
  const menor = conDatos.reduce<(typeof conDatos)[number] | null>((m, x) => (!m || x.t < m.t ? x : m), null);
  const franjas = (["valle", "resto", "pico"] as const).map((f) => ({ f, kwh: consumos.reduce((a, c) => a + c[f], 0) }));
  const origenes = (Object.keys(ETIQUETA_ORIGEN) as OrigenConsumo[])
    .map((o) => ({ o, n: consumos.filter((c) => c.origen === o).length }))
    .filter((x) => x.n > 0);

  return (
    <aside aria-label="Resumen anual de consumos" className="rounded-xl border border-borde bg-superficie xl:sticky xl:top-20">
      <div className="flex min-h-14 items-center border-b border-borde px-5 py-3">
        <h2 className="text-[15px] font-semibold text-tinta">Resumen anual</h2>
      </div>
      <div className="flex flex-col gap-5 p-5 text-sm">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 xl:grid-cols-1">
          <div className="col-span-2 xl:col-span-1">
            <dt className="text-[13px] text-tinta-2">Total anual</dt>
            <dd className="mt-0.5 text-2xl font-semibold tracking-[-0.01em] text-tinta tabular-nums">
              {fmt.entero(total)} <span className="text-sm font-normal text-tenue">kWh</span>
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-tinta-2">Promedio mensual</dt>
            <dd className="font-medium text-tinta tabular-nums">{conDatos.length ? `${fmt.entero(total / 12)} kWh` : "—"}</dd>
          </div>
          <div>
            <dt className="text-[13px] text-tinta-2">Mayor consumo</dt>
            <dd className="font-medium text-tinta tabular-nums">{mayor ? `${mayor.mes} · ${fmt.entero(mayor.t)} kWh` : "—"}</dd>
          </div>
          <div>
            <dt className="text-[13px] text-tinta-2">Menor consumo</dt>
            <dd className="font-medium text-tinta tabular-nums">{menor ? `${menor.mes} · ${fmt.entero(menor.t)} kWh` : "—"}</dd>
          </div>
        </dl>

        <div className="border-t border-borde pt-4">
          <h3 className="mb-2.5 text-[13px] font-medium text-tinta-2">Por franja</h3>
          <ul className="flex flex-col gap-2.5">
            {franjas.map(({ f, kwh }) => {
              const parte = total > 0 ? kwh / total : 0;
              return (
                <li key={f}>
                  <div className="flex items-baseline justify-between gap-2 tabular-nums">
                    <span className="text-tinta">{FRANJAS[f]}</span>
                    <span className="text-tinta-2">
                      {fmt.entero(kwh)} kWh <span className="ml-1 inline-block w-10 text-right font-medium text-tinta">{fmt.pct(parte)}</span>
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-superficie-2" aria-hidden>
                    <div className="h-full rounded-full bg-acento transition-[width] duration-200" style={{ width: `${parte * 100}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="border-t border-borde pt-4">
          <h3 className="mb-2.5 text-[13px] font-medium text-tinta-2">Origen de los datos</h3>
          <ul className="flex flex-wrap gap-x-3 gap-y-2">
            {origenes.map(({ o, n }) => (
              <li key={o} className="flex items-center gap-1.5 text-tinta-2 tabular-nums">
                <Insignia tono={TONO_ORIGEN[o]}>{ETIQUETA_ORIGEN[o]}</Insignia>
                {n} {n === 1 ? "mes" : "meses"}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}

function VisorFactura({ archivo }: { archivo: File | undefined }) {
  const url = useMemo(() => (archivo ? URL.createObjectURL(archivo) : null), [archivo]);
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  if (!archivo || !url) {
    return (
      <div className="flex h-full min-h-40 items-center justify-center rounded-lg border border-dashed border-borde-fuerte p-6 text-center text-sm text-tenue">
        El archivo original no está disponible en esta sesión.
      </div>
    );
  }
  return archivo.type === "application/pdf" ? (
    // Parámetros de apertura del visor: sin el panel de miniaturas y con la página ajustada al ancho
    // (navpanes/view: Chrome y Edge; pagemode: Firefox).
    <iframe
      src={`${url}#navpanes=0&pagemode=none&view=FitH`}
      title={archivo.name}
      className="h-[70vh] w-full rounded-lg border border-borde bg-superficie-2"
    />
  ) : (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt={archivo.name} className="max-h-[70vh] w-full rounded-lg border border-borde bg-superficie-2 object-contain" />
  );
}

export function PasoConsumos({
  consumos,
  alCambiar,
  extraccion,
  archivos,
  alConfirmar,
  alVolver,
}: {
  consumos: ConsumoMensual[];
  alCambiar: (c: ConsumoMensual[]) => void;
  extraccion: RespuestaExtraccion | null;
  archivos: File[];
  alConfirmar: () => void;
  alVolver: () => void;
}) {
  const [seleccionada, setSeleccionada] = useState(0);
  const factura = extraccion?.facturas[seleccionada];
  const sinFranjas = new Set(extraccion?.sugerencias.meses_sin_franjas ?? []);
  const vacios = consumos.map((c, i) => (c.valle + c.resto + c.pico === 0 ? MESES[i] : null)).filter(Boolean);
  const total = consumos.reduce((s, c) => s + c.valle + c.resto + c.pico, 0);

  const editar = (i: number, campo: "valle" | "resto" | "pico", v: number | null) =>
    alCambiar(consumos.map((c, j) => (j === i ? { ...c, [campo]: v ?? 0, origen: "manual" } : c)));

  const tabla = (
    <Seccion titulo="Consumos de los últimos 12 meses (kWh)">
      <div className="-mx-5 -mt-5 overflow-x-auto">
        <table className="w-full min-w-[680px] table-fixed border-collapse text-sm tabular-nums">
          <colgroup>
            <col className="w-24" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
            <col className="w-[15%]" />
            <col className="w-[13%]" />
            <col />
          </colgroup>
          <thead>
            <tr className="border-b border-borde bg-superficie-2 text-xs text-tinta-2">
              <th scope="col" className="py-2 pl-5 pr-3 text-left font-medium">
                Mes
              </th>
              <th scope="col" className="border-l border-borde px-3 text-right font-medium">
                Valle
              </th>
              <th scope="col" className="border-l border-borde px-3 text-right font-medium">
                Resto
              </th>
              <th scope="col" className="border-l border-borde px-3 text-right font-medium">
                Pico
              </th>
              <th scope="col" className="border-l border-borde px-3 text-right font-medium">
                Total
              </th>
              <th scope="col" className="pl-4 pr-5 text-left font-medium">
                Origen
              </th>
            </tr>
          </thead>
          <tbody>
            {consumos.map((c, i) => {
              const vacio = c.valle + c.resto + c.pico === 0;
              return (
                <tr key={MESES[i]} className="border-b border-borde">
                  <th scope="row" className="py-0 pl-5 pr-3 text-left text-[13px] font-medium text-tinta-2">
                    {MESES[i]}
                  </th>
                  {(["valle", "resto", "pico"] as const).map((campo) => (
                    <td key={campo} className="border-l border-borde p-0">
                      <Numero celda etiqueta={`${FRANJAS[campo]} ${MESES[i]}`} valor={c[campo]} alCambiar={(v) => editar(i, campo, v)} />
                    </td>
                  ))}
                  <td className={`border-l border-borde px-3 text-right font-medium ${vacio ? "text-tenue" : "text-tinta"}`}>
                    {fmt.entero(c.valle + c.resto + c.pico)}
                  </td>
                  <td className="py-1.5 pl-4 pr-5">
                    <span className="flex flex-wrap gap-1">
                      <Insignia tono={TONO_ORIGEN[c.origen]}>{c.origen}</Insignia>
                      {sinFranjas.has(i + 1) && c.origen !== "manual" && <Insignia tono="advertencia">sin franjas</Insignia>}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="bg-superficie-2 font-semibold">
              <th scope="row" className="py-2.5 pl-5 text-left" colSpan={4}>
                Total anual
              </th>
              <td className="border-l border-borde px-3 text-right">{fmt.entero(total)}</td>
              <td className="pr-5" />
            </tr>
          </tfoot>
        </table>
      </div>
      {(sinFranjas.size > 0 || vacios.length > 0) && (
        <div className="mt-4 space-y-2">
          {sinFranjas.size > 0 && (
            <Aviso nivel="advertencia">
              La tarifa no discrimina franjas horarias en algunos meses: el total quedó cargado como <b>resto</b>. Repartilo entre valle,
              resto y pico si tenés el dato; afecta el cálculo de excedentes.
            </Aviso>
          )}
          {vacios.length > 0 && <Aviso nivel="advertencia">Meses sin consumo cargado: {vacios.join(", ")}.</Aviso>}
        </div>
      )}
    </Seccion>
  );

  return (
    <div className="flex flex-1 flex-col gap-6">
      {extraccion && extraccion.facturas.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Seccion
            titulo="Factura"
            accion={
              extraccion.facturas.length > 1 && (
                <div className="w-full sm:w-64">
                  <Selector
                    aria-label="Factura a mostrar"
                    className="h-8 text-[13px]"
                    value={seleccionada}
                    onChange={(e) => setSeleccionada(Number(e.target.value))}
                  >
                    {extraccion.facturas.map((f, i) => (
                      <option key={i} value={i}>
                        {f.archivo}
                      </option>
                    ))}
                  </Selector>
                </div>
              )
            }
          >
            <VisorFactura archivo={archivos.find((a) => a.name === factura?.archivo)} />
          </Seccion>
          <Seccion titulo="Datos extraídos">
            {factura && (
              <>
                {factura.datos.tipo_documento !== "factura_distribuidora" && (
                  <div className="mb-3">
                    <Aviso nivel="advertencia">
                      El documento no parece una factura de distribuidora ({factura.datos.tipo_documento}); sus datos pueden no aplicar.
                    </Aviso>
                  </div>
                )}
                <dl className="divide-y divide-borde text-sm">
                  {CAMPOS.map(([clave, etiqueta]) => {
                    const campo = factura.datos[clave] as CampoConfianza<string | number> | undefined;
                    const dudoso = campo && campo.valor != null && campo.confianza < UMBRAL;
                    return (
                      <div
                        key={clave}
                        className={`flex items-baseline justify-between gap-4 px-2 py-1.5 ${dudoso ? "rounded-md bg-advertencia/12" : ""}`}
                      >
                        <dt className="text-tinta-2">{etiqueta}</dt>
                        <dd className="flex items-baseline gap-2 text-right font-medium tabular-nums text-tinta">
                          {dudoso && <Insignia tono="advertencia">revisar</Insignia>}
                          {campo?.valor == null ? (
                            <span className="text-tenue">—</span>
                          ) : clave === "periodo_mes" && typeof campo.valor === "number" ? (
                            `${MESES[campo.valor - 1] ?? campo.valor} (${campo.valor})`
                          ) : clave === "periodo_anio" ? (
                            String(campo.valor)
                          ) : typeof campo.valor === "number" ? (
                            fmt.n(campo.valor, 2)
                          ) : (
                            campo.valor
                          )}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
                {factura.datos.notas && <p className="mt-3 text-xs text-tinta-2">Notas: {factura.datos.notas}</p>}
              </>
            )}
            <div className="mt-4 rounded-lg border border-borde bg-superficie-2 px-3.5 py-3 text-sm">
              <p className="font-medium text-tinta">Costo de distribuidora sugerido</p>
              <p className="mt-0.5 text-tinta-2">
                Importe básico / kWh:{" "}
                <b className="font-semibold text-tinta tabular-nums">{fmt.n(extraccion.sugerencias.costo_distribuidora, 2)} $/kWh</b>
                {extraccion.sugerencias.costo_energia_activa != null && (
                  <>
                    {" "}
                    · solo energía activa:{" "}
                    <b className="font-semibold text-tinta tabular-nums">{fmt.n(extraccion.sugerencias.costo_energia_activa, 2)} $/kWh</b>
                  </>
                )}
              </p>
            </div>
          </Seccion>
        </div>
      ) : (
        <Aviso nivel="info">Carga manual: completá los consumos mensuales de valle, resto y pico.</Aviso>
      )}
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
        {tabla}
        <ResumenConsumos consumos={consumos} />
      </div>
      <BarraAcciones>
        <Boton variante="secundario" onClick={alVolver} icono={<ArrowLeft aria-hidden />}>
          Volver
        </Boton>
        <Boton onClick={alConfirmar} deshabilitado={total === 0}>
          Confirmar consumos
        </Boton>
      </BarraAcciones>
    </div>
  );
}
