"use client";

import { ChevronDown, CircleAlert, CircleX, Info, LoaderCircle, Monitor, Moon, Sun, SunMedium, TriangleAlert } from "lucide-react";
import { isValidElement, useState, type ReactNode } from "react";
import { aplicarTema, leerTema, type Tema } from "@/lib/tema";

export function Seccion({
  titulo,
  children,
  accion,
  id,
}: {
  titulo: string;
  children: ReactNode;
  accion?: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-titulo` : undefined} className="rounded-xl border border-borde bg-superficie">
      <div className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-borde px-5 py-3">
        <h2 id={id ? `${id}-titulo` : undefined} className="text-[15px] font-semibold text-tinta">
          {titulo}
        </h2>
        {accion}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Grilla({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-x-4 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{children}</div>;
}

export function Campo({
  etiqueta,
  ayuda,
  error,
  children,
  ancho,
}: {
  etiqueta: string;
  ayuda?: string;
  error?: string;
  children: ReactNode;
  ancho?: 2 | 4;
}) {
  const span = ancho === 4 ? "sm:col-span-2 lg:col-span-3 xl:col-span-4" : ancho === 2 ? "sm:col-span-2" : "";
  const titulo = <span className="text-[13px] font-medium leading-5 text-tinta-2">{etiqueta}</span>;
  return (
    <div className={`group flex flex-col gap-1.5 ${span}`} data-invalido={error ? true : undefined}>
      {isValidElement(children) && children.type === SiNo ? (
        // Un grupo de botones se nombra con fieldset/legend; un <label> nombraría solo al primero.
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5">{titulo}</legend>
          {children}
        </fieldset>
      ) : (
        <label className="flex flex-col gap-1.5">
          {titulo}
          {children}
        </label>
      )}
      {error ? (
        <span className="flex items-start gap-1 text-xs leading-4 text-critico-texto">
          <CircleAlert aria-hidden className="mt-px size-3.5 shrink-0" />
          {error}
        </span>
      ) : ayuda ? (
        <span className="text-xs leading-4 text-tenue">{ayuda}</span>
      ) : null}
    </div>
  );
}

/** "1.540,5" → 1540.5 · "146.77" → 146.77 (con coma, los puntos son miles). */
export function leerNumero(t: string): number {
  const limpio = t.trim().replace(/\s/g, "");
  return Number(limpio.includes(",") ? limpio.replace(/\./g, "").replace(",", ".") : limpio);
}

export const claseInput =
  "h-9 w-full rounded-md border border-borde-fuerte bg-superficie px-3 text-sm text-tinta tabular-nums outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-tenue hover:border-eje focus:border-acento focus:ring-3 focus:ring-acento/20 disabled:cursor-not-allowed disabled:bg-superficie-2 disabled:text-tenue group-data-invalido:border-critico group-data-invalido:focus:ring-critico/20";

/** Número editable. `porcentaje` muestra 0,12 como 12. Acepta coma decimal. */
export function Numero({
  valor,
  alCambiar,
  porcentaje,
  min,
  paso,
  sufijo,
  deshabilitado,
  vacioEsNulo,
  compacto,
  etiqueta,
}: {
  valor: number | null;
  alCambiar: (v: number | null) => void;
  porcentaje?: boolean;
  min?: number;
  paso?: number;
  sufijo?: string;
  deshabilitado?: boolean;
  vacioEsNulo?: boolean;
  /** Celda de tabla: más baja y alineada a la derecha para leer columnas de cifras. */
  compacto?: boolean;
  /** Nombre accesible cuando el campo no tiene un <label> visible (celdas de tabla). */
  etiqueta?: string;
}) {
  const mostrar = (v: number | null) =>
    v == null ? "" : String(porcentaje ? Number((v * 100).toFixed(6)) : v).replace(".", ",");
  const [texto, setTexto] = useState(mostrar(valor));
  const [previo, setPrevio] = useState(valor);
  if (valor !== previo) {
    // El valor cambió desde afuera: se re-sincroniza el texto salvo que ya lo represente.
    setPrevio(valor);
    const actual = texto.trim() === "" ? null : leerNumero(texto);
    const comparable = actual == null ? null : porcentaje ? actual / 100 : actual;
    if (comparable !== valor) setTexto(mostrar(valor));
  }
  const conSufijo = Boolean(sufijo || porcentaje);

  return (
    <div className="relative">
      <input
        className={`${claseInput} ${compacto ? "h-8 px-2 text-right" : ""} ${conSufijo ? (sufijo && sufijo.length > 3 ? "pr-20" : "pr-10") : ""}`}
        inputMode="decimal"
        value={texto}
        disabled={deshabilitado}
        min={min}
        step={paso}
        aria-label={etiqueta}
        onChange={(ev) => {
          const t = ev.target.value;
          setTexto(t);
          if (t.trim() === "") return alCambiar(vacioEsNulo ? null : 0);
          const n = leerNumero(t);
          if (!Number.isNaN(n)) alCambiar(porcentaje ? n / 100 : n);
        }}
      />
      {conSufijo && (
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-tenue">
          {porcentaje ? "%" : sufijo}
        </span>
      )}
    </div>
  );
}

export function Texto({ valor, alCambiar }: { valor: string; alCambiar: (v: string) => void }) {
  return <input className={claseInput} value={valor} onChange={(e) => alCambiar(e.target.value)} />;
}

/** <select> nativo con la flecha del sistema de diseño. */
export function Selector({
  children,
  className = "",
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <div className="relative">
      <select {...props} className={`${claseInput} cursor-pointer appearance-none pr-9 disabled:cursor-not-allowed ${className}`}>
        {children}
      </select>
      <ChevronDown aria-hidden className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-tenue" />
    </div>
  );
}

export function Opciones<T extends string | number>({
  valor,
  opciones,
  alCambiar,
  deshabilitado,
  etiquetas,
}: {
  valor: T | null;
  opciones: readonly T[];
  alCambiar: (v: T) => void;
  deshabilitado?: boolean;
  etiquetas?: (v: T) => string;
}) {
  return (
    <Selector
      value={valor == null ? "" : String(valor)}
      disabled={deshabilitado}
      onChange={(e) => {
        const elegido = opciones.find((o) => String(o) === e.target.value);
        if (elegido !== undefined) alCambiar(elegido);
      }}
    >
      {valor == null && <option value="">Elegir…</option>}
      {opciones.map((o) => (
        <option key={String(o)} value={String(o)}>
          {etiquetas ? etiquetas(o) : String(o)}
        </option>
      ))}
    </Selector>
  );
}

export function SiNo({ valor, alCambiar, deshabilitado }: { valor: boolean; alCambiar: (v: boolean) => void; deshabilitado?: boolean }) {
  return (
    <div className="grid h-9 grid-cols-2 gap-0.5 rounded-md border border-borde-fuerte bg-superficie-2 p-0.5" role="radiogroup">
      {[true, false].map((v) => (
        <button
          key={String(v)}
          type="button"
          role="radio"
          aria-checked={valor === v}
          disabled={deshabilitado}
          onClick={() => alCambiar(v)}
          className={`rounded-[5px] text-sm transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
            valor === v ? "bg-acento font-medium text-sobre-acento" : "text-tinta-2 hover:bg-superficie hover:text-tinta"
          }`}
        >
          {v ? "Sí" : "No"}
        </button>
      ))}
    </div>
  );
}

export function Boton({
  children,
  onClick,
  variante = "primario",
  deshabilitado,
  cargando,
  tipo = "button",
  icono,
  titulo,
}: {
  children: ReactNode;
  onClick?: () => void;
  variante?: "primario" | "secundario" | "fantasma";
  deshabilitado?: boolean;
  cargando?: boolean;
  tipo?: "button" | "submit";
  /** Ícono a la izquierda del texto; mientras carga se reemplaza por el indicador. */
  icono?: ReactNode;
  titulo?: string;
}) {
  const estilos = {
    primario: "bg-acento text-sobre-acento hover:bg-acento-fuerte active:bg-acento-fuerte",
    secundario: "border border-borde-fuerte bg-superficie text-tinta hover:bg-superficie-2 active:bg-borde",
    fantasma: "text-tinta-2 hover:bg-superficie-2 hover:text-tinta active:bg-borde",
  }[variante];
  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={deshabilitado || cargando}
      title={titulo}
      aria-busy={cargando || undefined}
      className={`inline-flex h-9 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3.5 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:size-4 ${estilos}`}
    >
      {cargando ? <LoaderCircle aria-hidden className="animate-spin" /> : icono}
      {children}
    </button>
  );
}

export function Aviso({ nivel, children }: { nivel: "error" | "advertencia" | "info"; children: ReactNode }) {
  const estilo = {
    error: "border-critico/30 bg-critico/[0.07]",
    advertencia: "border-advertencia/40 bg-advertencia/[0.09]",
    info: "border-acento/25 bg-acento-suave",
  }[nivel];
  const Icono = { error: CircleX, advertencia: TriangleAlert, info: Info }[nivel];
  const tono = { error: "text-critico-texto", advertencia: "text-advertencia-texto", info: "text-acento" }[nivel];
  const etiqueta = { error: "Error", advertencia: "Advertencia", info: "Info" }[nivel];
  return (
    <div className={`flex gap-2.5 rounded-lg border px-3.5 py-3 text-sm leading-5 text-tinta ${estilo}`} role={nivel === "error" ? "alert" : "status"}>
      <Icono role="img" aria-label={etiqueta} className={`mt-px size-4 shrink-0 ${tono}`} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function Insignia({ children, tono }: { children: ReactNode; tono: "neutro" | "acento" | "advertencia" | "bueno" }) {
  const estilos = {
    neutro: "bg-superficie-2 text-tinta-2 ring-borde",
    acento: "bg-acento-suave text-acento-fuerte ring-acento/25",
    advertencia: "bg-advertencia/12 text-advertencia-texto ring-advertencia/35",
    bueno: "bg-bueno/10 text-bueno-texto ring-bueno/30",
  }[tono];
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-md px-1.5 py-px text-xs font-medium ring-1 ring-inset ${estilos}`}>
      {children}
    </span>
  );
}

/** Barra fija al pie con la navegación del paso: Volver a la izquierda, la acción principal a la derecha. */
export function BarraAcciones({ children }: { children: ReactNode }) {
  return (
    <div className="sticky bottom-0 z-20 -mx-4 mt-2 border-t border-borde bg-plano px-4 py-3 sm:-mx-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">{children}</div>
    </div>
  );
}

/** Marca de la aplicación: sol sobre el acento, nombre del estudio y de la empresa. */
export function Marca() {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span aria-hidden className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-acento text-sobre-acento">
        <SunMedium className="size-[18px]" strokeWidth={2.25} />
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <h1 className="truncate text-sm font-semibold text-tinta">Estudio de prefactibilidad solar</h1>
        <span className="truncate text-xs text-tenue">Dynamic Energy</span>
      </span>
    </div>
  );
}

const TEMAS: { valor: Tema; etiqueta: string; Icono: typeof Sun }[] = [
  { valor: "sistema", etiqueta: "Tema del sistema", Icono: Monitor },
  { valor: "claro", etiqueta: "Tema claro", Icono: Sun },
  { valor: "oscuro", etiqueta: "Tema oscuro", Icono: Moon },
];

export function SelectorTema() {
  const [tema, setTema] = useState<Tema>(leerTema);
  return (
    <div role="radiogroup" aria-label="Tema" className="flex h-8 items-center gap-0.5 rounded-md border border-borde bg-superficie-2 p-0.5">
      {TEMAS.map(({ valor, etiqueta, Icono }) => (
        <button
          key={valor}
          type="button"
          role="radio"
          aria-checked={tema === valor}
          aria-label={etiqueta}
          title={etiqueta}
          onClick={() => {
            setTema(valor);
            aplicarTema(valor);
          }}
          className={`flex size-7 items-center justify-center rounded-[5px] transition-colors duration-150 ${
            tema === valor ? "bg-superficie text-tinta ring-1 ring-borde-fuerte" : "text-tenue hover:text-tinta"
          }`}
        >
          <Icono aria-hidden className="size-3.5" />
        </button>
      ))}
    </div>
  );
}
