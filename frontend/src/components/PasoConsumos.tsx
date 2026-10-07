"use client";

import { useEffect, useMemo, useState } from "react";
import { fmt, MESES } from "@/lib/estado";
import type { CampoConfianza, ConsumoMensual, OrigenConsumo, RespuestaExtraccion } from "@/lib/tipos";
import { Aviso, Boton, Insignia, Numero, Seccion } from "./ui";

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

function VisorFactura({ archivo }: { archivo: File | undefined }) {
  const url = useMemo(() => (archivo ? URL.createObjectURL(archivo) : null), [archivo]);
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  if (!archivo || !url) {
    return <div className="flex h-full items-center justify-center p-6 text-sm text-tenue">El archivo original no está disponible en esta sesión.</div>;
  }
  return archivo.type === "application/pdf" ? (
    <iframe src={url} title={archivo.name} className="h-[70vh] w-full rounded-md" />
  ) : (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt={archivo.name} className="max-h-[70vh] w-full rounded-md object-contain" />
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
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="border-b border-borde text-left text-xs text-tenue">
              <th className="py-2 pr-2 font-medium">Mes</th>
              <th className="px-2 font-medium">Valle</th>
              <th className="px-2 font-medium">Resto</th>
              <th className="px-2 font-medium">Pico</th>
              <th className="px-2 text-right font-medium">Total</th>
              <th className="pl-2 font-medium">Origen</th>
            </tr>
          </thead>
          <tbody>
            {consumos.map((c, i) => (
              <tr key={MESES[i]} className="border-b border-borde/60 last:border-0">
                <td className="py-1.5 pr-2 font-medium text-tinta-2">{MESES[i]}</td>
                {(["valle", "resto", "pico"] as const).map((campo) => (
                  <td key={campo} className="px-1 py-1">
                    <Numero valor={c[campo]} alCambiar={(v) => editar(i, campo, v)} />
                  </td>
                ))}
                <td className="px-2 text-right text-tinta">{fmt.entero(c.valle + c.resto + c.pico)}</td>
                <td className="pl-2">
                  <span className="flex flex-wrap gap-1">
                    <Insignia tono={TONO_ORIGEN[c.origen]}>{c.origen}</Insignia>
                    {sinFranjas.has(i + 1) && c.origen !== "manual" && <Insignia tono="advertencia">sin franjas</Insignia>}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-borde font-semibold">
              <td className="py-2" colSpan={4}>
                Total anual
              </td>
              <td className="px-2 text-right">{fmt.entero(total)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
      <div className="mt-4 space-y-2">
        {sinFranjas.size > 0 && (
          <Aviso nivel="advertencia">
            La tarifa no discrimina franjas horarias en algunos meses: el total quedó cargado como <b>resto</b>. Repartilo entre valle,
            resto y pico si tenés el dato; afecta el cálculo de excedentes.
          </Aviso>
        )}
        {vacios.length > 0 && <Aviso nivel="advertencia">Meses sin consumo cargado: {vacios.join(", ")}.</Aviso>}
      </div>
    </Seccion>
  );

  return (
    <div className="space-y-6">
      {extraccion && extraccion.facturas.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Seccion
            titulo="Factura"
            accion={
              extraccion.facturas.length > 1 && (
                <select
                  className="rounded-md border border-borde bg-plano px-2 py-1 text-sm"
                  value={seleccionada}
                  onChange={(e) => setSeleccionada(Number(e.target.value))}
                >
                  {extraccion.facturas.map((f, i) => (
                    <option key={i} value={i}>
                      {f.archivo}
                    </option>
                  ))}
                </select>
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
                <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
                  {CAMPOS.map(([clave, etiqueta]) => {
                    const campo = factura.datos[clave] as CampoConfianza<string | number> | undefined;
                    const dudoso = campo && campo.valor != null && campo.confianza < UMBRAL;
                    return (
                      <div key={clave} className={`flex justify-between gap-2 rounded px-2 py-1 ${dudoso ? "bg-advertencia/20" : ""}`}>
                        <dt className="text-tinta-2">{etiqueta}</dt>
                        <dd className="text-right font-medium tabular-nums text-tinta">
                          {campo?.valor == null ? "—" : typeof campo.valor === "number" ? fmt.n(campo.valor, 2) : campo.valor}
                          {dudoso && <span className="ml-1 text-xs text-tinta-2">(revisar)</span>}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
                {factura.datos.notas && <p className="mt-3 text-xs text-tinta-2">Notas: {factura.datos.notas}</p>}
              </>
            )}
            <div className="mt-4 border-t border-borde pt-3 text-sm">
              <p className="font-medium text-tinta">Costo de distribuidora sugerido</p>
              <p className="text-tinta-2">
                Importe básico / kWh: <b className="text-tinta">{fmt.n(extraccion.sugerencias.costo_distribuidora, 2)} $/kWh</b>
                {extraccion.sugerencias.costo_energia_activa != null && (
                  <>
                    {" "}
                    · solo energía activa: <b className="text-tinta">{fmt.n(extraccion.sugerencias.costo_energia_activa, 2)} $/kWh</b>
                  </>
                )}
              </p>
            </div>
          </Seccion>
        </div>
      ) : (
        <Aviso nivel="info">Carga manual: completá los consumos mensuales de valle, resto y pico.</Aviso>
      )}
      {tabla}
      <div className="flex justify-between">
        <Boton variante="secundario" onClick={alVolver}>
          Volver
        </Boton>
        <Boton onClick={alConfirmar} deshabilitado={total === 0}>
          Confirmar consumos
        </Boton>
      </div>
    </div>
  );
}
