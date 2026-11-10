"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmt } from "@/lib/estado";
import type { Resultado } from "@/lib/tipos";

const EJE = { stroke: "var(--eje)", tick: { fill: "var(--tenue)", fontSize: 12 }, tickLine: false };
const GRILLA = <CartesianGrid stroke="var(--borde)" strokeWidth={1} vertical={false} />;
const TOOLTIP = {
  contentStyle: {
    background: "var(--superficie)",
    border: "1px solid var(--borde)",
    borderRadius: 8,
    color: "var(--tinta)",
    fontSize: 13,
    boxShadow: "0 4px 12px rgb(0 0 0 / 0.12)",
    padding: "8px 10px",
  },
  labelStyle: { color: "var(--tinta)", fontWeight: 600 },
  itemStyle: { color: "var(--tinta-2)" },
  cursor: { fill: "var(--borde)", opacity: 0.4 },
};
// El texto de la leyenda va en tinta neutra; el color lo lleva solo el marcador.
const LEYENDA = {
  wrapperStyle: { fontSize: 13 },
  iconType: "square" as const,
  iconSize: 10,
  itemSorter: null,
  formatter: (valor: string) => <span style={{ color: "var(--tinta-2)" }}>{valor}</span>,
};
const miles = (v: number) => (Math.abs(v) >= 1000 ? `${fmt.n(v / 1000)} k` : fmt.n(v));

function Marco({ titulo, descripcion, children }: { titulo: string; descripcion: string; children: React.ReactNode }) {
  return (
    <figure className="flex flex-col rounded-xl border border-borde bg-superficie">
      <figcaption className="flex min-h-14 flex-col justify-center border-b border-borde px-5 py-2.5">
        <span className="text-[15px] font-semibold text-tinta">{titulo}</span>
        <span className="text-xs text-tenue">{descripcion}</span>
      </figcaption>
      <div className="h-72 px-3 pb-3 pt-4">{children}</div>
    </figure>
  );
}

export function GraficoMensual({ r }: { r: Resultado }) {
  const datos = r.mensual.map((m) => ({ mes: m.mes, Consumo: m.consumo_kwh, Generación: m.generacion_kwh }));
  return (
    <Marco titulo="Consumo vs. generación" descripcion="kWh por mes">
      <ResponsiveContainer>
        <BarChart data={datos} barGap={2} barCategoryGap="20%">
          {GRILLA}
          <XAxis dataKey="mes" {...EJE} />
          <YAxis {...EJE} axisLine={false} tickFormatter={miles} width={48} />
          <Tooltip {...TOOLTIP} formatter={(v) => `${fmt.entero(Number(v))} kWh`} />
          <Legend {...LEYENDA} />
          <Bar dataKey="Consumo" fill="var(--serie-1)" radius={[4, 4, 0, 0]} maxBarSize={18} />
          <Bar dataKey="Generación" fill="var(--serie-2)" radius={[4, 4, 0, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </Marco>
  );
}

export function GraficoRoi({ r }: { r: Resultado }) {
  // El eje llega unos años más allá del repago de cada caso, no a un 25 fijo.
  const anios = r.anios_curva_roi;
  const datos = r.curva_roi.slice(0, anios).map((capital, i) => ({ anio: i + 1, capital }));
  const paso = anios <= 10 ? 1 : anios <= 16 ? 2 : 5;
  const marcas = Array.from({ length: Math.floor((anios - 1) / paso) + 1 }, (_, i) => 1 + i * paso);
  return (
    <Marco
      titulo="Retorno de la inversión"
      descripcion={`Capital acumulado en U$D · recupera en ${fmt.anios(r.roi_anios)}`}
    >
      <ResponsiveContainer>
        <LineChart data={datos}>
          {GRILLA}
          <XAxis dataKey="anio" type="number" domain={[1, anios]} ticks={marcas} {...EJE} />
          <YAxis {...EJE} axisLine={false} tickFormatter={miles} width={56} />
          <Tooltip
            {...TOOLTIP}
            cursor={{ stroke: "var(--eje)" }}
            labelFormatter={(v) => `Año ${v}`}
            formatter={(v) => [fmt.usd(Number(v)), "Capital"]}
          />
          <ReferenceLine y={0} stroke="var(--tinta-2)" />
          {r.roi_anios != null && r.roi_anios <= anios && (
            <ReferenceLine
              x={r.roi_anios}
              stroke="var(--tenue)"
              strokeDasharray="4 4"
              label={{ value: "repago", position: "insideTopRight", fill: "var(--tinta-2)", fontSize: 12 }}
            />
          )}
          <Line dataKey="capital" stroke="var(--serie-1)" strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </Marco>
  );
}

export function GraficoFinanciacion({ r }: { r: Resultado }) {
  const f = r.financiacion;
  // Por semestre: pagos y ahorros en barras, ahorro acumulado en línea.
  const datos = f.pagos_semestrales.map((p, i) => ({
    semestre: `S${i + 1}`,
    Pagos: p,
    Ahorros: f.ahorros_semestrales[i],
    "Ahorro acumulado": f.ahorro_acumulado_semestral[i],
  }));
  return (
    <Marco titulo="Financiamiento: pagos vs. ahorros" descripcion="U$D por semestre, primeros 7 años · el ahorro acumulado va en línea">
      <ResponsiveContainer>
        <ComposedChart data={datos} barGap={2} barCategoryGap="25%">
          {GRILLA}
          <XAxis dataKey="semestre" {...EJE} />
          <YAxis {...EJE} axisLine={false} tickFormatter={miles} width={48} />
          <Tooltip {...TOOLTIP} formatter={(v) => fmt.usd(Number(v))} />
          <Legend {...LEYENDA} />
          <Bar dataKey="Pagos" fill="var(--serie-1)" radius={[4, 4, 0, 0]} maxBarSize={20} />
          <Bar dataKey="Ahorros" fill="var(--serie-2)" radius={[4, 4, 0, 0]} maxBarSize={20} />
          <Line dataKey="Ahorro acumulado" stroke="var(--tinta)" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </Marco>
  );
}
