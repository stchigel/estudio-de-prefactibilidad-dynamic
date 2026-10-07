"use client";

import { isValidElement, useState, type ReactNode } from "react";

export function Seccion({ titulo, children, accion }: { titulo: string; children: ReactNode; accion?: ReactNode }) {
  return (
    <section className="rounded-lg border border-borde bg-superficie p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-tinta">{titulo}</h2>
        {accion}
      </div>
      {children}
    </section>
  );
}

export function Grilla({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">{children}</div>;
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
  const span = ancho === 4 ? "sm:col-span-2 lg:col-span-4" : ancho === 2 ? "sm:col-span-2" : "";
  return (
    <div className={`flex flex-col gap-1 text-sm ${span}`}>
      {isValidElement(children) && children.type === SiNo ? (
        // Un grupo de botones se nombra con fieldset/legend; un <label> nombraría solo al primero.
        <fieldset className="flex flex-col gap-1">
          <legend className="mb-1 font-medium text-tinta-2">{etiqueta}</legend>
          {children}
        </fieldset>
      ) : (
        <label className="flex flex-col gap-1">
          <span className="font-medium text-tinta-2">{etiqueta}</span>
          {children}
        </label>
      )}
      {error ? <span className="text-xs text-critico">{error}</span> : ayuda ? <span className="text-xs text-tenue">{ayuda}</span> : null}
    </div>
  );
}

/** "1.540,5" → 1540.5 · "146.77" → 146.77 (con coma, los puntos son miles). */
export function leerNumero(t: string): number {
  const limpio = t.trim().replace(/\s/g, "");
  return Number(limpio.includes(",") ? limpio.replace(/\./g, "").replace(",", ".") : limpio);
}

const claseInput =
  "w-full rounded-md border border-borde bg-plano px-3 py-2 text-sm text-tinta tabular-nums outline-none focus:border-acento focus:ring-2 focus:ring-acento/30 disabled:opacity-50";

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
}: {
  valor: number | null;
  alCambiar: (v: number | null) => void;
  porcentaje?: boolean;
  min?: number;
  paso?: number;
  sufijo?: string;
  deshabilitado?: boolean;
  vacioEsNulo?: boolean;
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

  return (
    <div className="relative">
      <input
        className={`${claseInput} ${sufijo || porcentaje ? "pr-12" : ""}`}
        inputMode="decimal"
        value={texto}
        disabled={deshabilitado}
        min={min}
        step={paso}
        onChange={(ev) => {
          const t = ev.target.value;
          setTexto(t);
          if (t.trim() === "") return alCambiar(vacioEsNulo ? null : 0);
          const n = leerNumero(t);
          if (!Number.isNaN(n)) alCambiar(porcentaje ? n / 100 : n);
        }}
      />
      {(sufijo || porcentaje) && (
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
    <select
      className={claseInput}
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
    </select>
  );
}

export function SiNo({ valor, alCambiar, deshabilitado }: { valor: boolean; alCambiar: (v: boolean) => void; deshabilitado?: boolean }) {
  return (
    <div className="flex gap-1 rounded-md border border-borde bg-plano p-1" role="radiogroup">
      {[true, false].map((v) => (
        <button
          key={String(v)}
          type="button"
          role="radio"
          aria-checked={valor === v}
          disabled={deshabilitado}
          onClick={() => alCambiar(v)}
          className={`flex-1 rounded px-3 py-1 text-sm transition disabled:opacity-50 ${
            valor === v ? "bg-acento text-white" : "text-tinta-2 hover:bg-borde/50"
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
}: {
  children: ReactNode;
  onClick?: () => void;
  variante?: "primario" | "secundario" | "fantasma";
  deshabilitado?: boolean;
  cargando?: boolean;
  tipo?: "button" | "submit";
}) {
  const estilos = {
    primario: "bg-acento text-white hover:bg-acento-fuerte",
    secundario: "border border-borde bg-superficie text-tinta hover:bg-plano",
    fantasma: "text-tinta-2 hover:bg-plano",
  }[variante];
  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={deshabilitado || cargando}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${estilos}`}
    >
      {cargando && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  );
}

export function Aviso({ nivel, children }: { nivel: "error" | "advertencia" | "info"; children: ReactNode }) {
  const estilo = {
    error: "border-critico/40 bg-critico/10",
    advertencia: "border-advertencia/50 bg-advertencia/10",
    info: "border-acento/30 bg-acento/5",
  }[nivel];
  const icono = { error: "✕", advertencia: "!", info: "i" }[nivel];
  const etiqueta = { error: "Error", advertencia: "Advertencia", info: "Info" }[nivel];
  return (
    <div className={`flex gap-3 rounded-md border px-4 py-3 text-sm text-tinta ${estilo}`} role={nivel === "error" ? "alert" : "status"}>
      <span aria-label={etiqueta} className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-xs font-bold">
        {icono}
      </span>
      <div>{children}</div>
    </div>
  );
}

export function Insignia({ children, tono }: { children: ReactNode; tono: "neutro" | "acento" | "advertencia" | "bueno" }) {
  const estilos = {
    neutro: "bg-borde/60 text-tinta-2",
    acento: "bg-acento/15 text-acento-fuerte",
    advertencia: "bg-advertencia/20 text-tinta",
    bueno: "bg-bueno/15 text-bueno-texto",
  }[tono];
  return <span className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${estilos}`}>{children}</span>;
}
