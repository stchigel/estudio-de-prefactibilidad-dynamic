import type { ConsumoMensual, Entradas, RespuestaExtraccion } from "./tipos";

export const MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];

export const PASOS = ["Facturas", "Consumos", "Proyecto", "Opciones", "Resultados"] as const;
export type Paso = (typeof PASOS)[number];

export function consumoVacio(): ConsumoMensual {
  return { valle: 0, resto: 0, pico: 0, origen: "manual" };
}

export function entradasIniciales(): Entradas {
  return {
    dolar: 0,
    numero_propuesta: null,
    fecha: new Date().toISOString().slice(0, 10),
    cliente: "",
    provincia: "Buenos Aires",
    categoria: "Industrial < 300kW",
    distribuidora: "",
    tarifa: "",
    potencia_contratada_kw: 0,
    horario_trabajo: "Lu a Vi",
    horas_por_dia: 8,
    m2_disponibles: null,
    origen_m2: null,
    costo_mayorista: 0,
    tasa_mayorista: 0,
    costo_cammesa: 0,
    tasa_cammesa: 0,
    potencia_contratada_cammesa_kw: null,
    costo_distribuidora: 0,
    tasas_mun_prov: 0,
    tasa_976: 0,
    res281_usd_mwh: 0,
    retribucion_inyeccion: 0,
    tipo_inversor: "ON GRID",
    inhibicion_inyeccion: true,
    banco_capacitores: false,
    instalacion: "Coplanar",
    acimut: 0,
    inclinacion: 15,
    inversor: "Growatt",
    kit1: { kwp: 11.02, cantidad: 1, distancia_tgbt_m: 0 },
    kit2: null,
    baterias: { incluye: false, objetivo: "--", autonomia_h: 0, modelo: null, cantidad: 0, cantidad_pdu: 0, cantidad_rack: 0 },
    k_incertidumbre: 0,
    comision: 0,
    tasa_descuento: 0.12,
    periodo_evaluacion: 25,
    capacitores: { kvar: 0, inversion_usd: 0, ahorro_ars_anio: 0 },
    financiacion: { porcentaje: 0, tipo: "Prestamo", moneda: "U$D", plazo_anios: 0, gracia_anios: 0, tasa: 0, gastos_adm: 0 },
    ppa: { aplica: false, periodo_contrato: 7, precio_usd_mwh: 0, inflacion_usd: 0, fee_salida_usd: 0, oem: 0 },
    consumos: MESES.map(consumoVacio),
  };
}

/**
 * Parámetros de mercado y criterios de la empresa: cambian poco entre análisis,
 * así que se arrastran a la propuesta siguiente. El resto es propio de cada cliente.
 */
const CAMPOS_PERSISTENTES = [
  "dolar",
  "costo_mayorista",
  "tasa_mayorista",
  "costo_cammesa",
  "tasa_cammesa",
  "tasa_976",
  "res281_usd_mwh",
  "k_incertidumbre",
  "comision",
  "tasa_descuento",
  "periodo_evaluacion",
] as const satisfies readonly (keyof Entradas)[];

/** Entradas en blanco para un análisis nuevo, conservando solo los campos persistentes. */
export function entradasNuevoAnalisis(previas: Entradas): Entradas {
  const e = entradasIniciales();
  for (const campo of CAMPOS_PERSISTENTES) (e as unknown as Record<string, unknown>)[campo] = previas[campo];
  return e;
}

export interface Borrador {
  paso: Paso;
  entradas: Entradas;
  extraccion: RespuestaExtraccion | null;
}

const CLAVE = "prefactibilidad:borrador";

export function leerBorrador(): Borrador | null {
  try {
    const texto = localStorage.getItem(CLAVE);
    return texto ? (JSON.parse(texto) as Borrador) : null;
  } catch {
    return null;
  }
}

export function guardarBorrador(b: Borrador): void {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(b));
  } catch {
    /* almacenamiento no disponible: el borrador vive solo en memoria */
  }
}

export function borrarBorrador(): void {
  try {
    localStorage.removeItem(CLAVE);
  } catch {
    /* nada */
  }
}

/** Aplica las sugerencias extraídas de las facturas a las entradas (§5.4). */
export function aplicarSugerencias(e: Entradas, r: RespuestaExtraccion): Entradas {
  const s = r.sugerencias;
  return {
    ...e,
    cliente: s.cliente ?? e.cliente,
    provincia: s.provincia ?? e.provincia,
    distribuidora: s.distribuidora ?? e.distribuidora,
    tarifa: s.tarifa ?? e.tarifa,
    potencia_contratada_kw: s.potencia_contratada_kw ?? e.potencia_contratada_kw,
    costo_distribuidora: s.costo_distribuidora ?? e.costo_distribuidora,
    tasas_mun_prov: s.tasas_mun_prov ?? e.tasas_mun_prov,
    consumos: s.consumos.map((c, i) => c ?? e.consumos[i] ?? consumoVacio()),
  };
}

const ars = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const usd = new Intl.NumberFormat("es-AR", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const fmt = {
  n: (v: number | null | undefined, dec = 0) =>
    v == null ? "—" : v.toLocaleString("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec }),
  entero: (v: number | null | undefined) => (v == null ? "—" : ars.format(v)),
  usd: (v: number | null | undefined) => (v == null ? "—" : usd.format(v)),
  pct: (v: number | null | undefined, dec = 0) =>
    v == null ? "—" : `${(v * 100).toLocaleString("es-AR", { maximumFractionDigits: dec })} %`,
  anios: (v: number | null | undefined) => (v == null ? "sin repago" : `${v.toLocaleString("es-AR", { maximumFractionDigits: 1 })} años`),
};
