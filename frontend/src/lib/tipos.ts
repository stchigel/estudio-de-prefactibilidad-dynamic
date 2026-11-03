// Espejo de backend/motor/modelos.py y extraccion/derivados.py

export type OrigenConsumo = "factura" | "historial" | "estimado" | "manual";

export interface ConsumoMensual {
  valle: number;
  resto: number;
  pico: number;
  origen: OrigenConsumo;
}

export interface Kit {
  kwp: number;
  cantidad: number;
  distancia_tgbt_m: number;
}

export interface Baterias {
  incluye: boolean;
  objetivo: string;
  autonomia_h: number;
  modelo: string | null;
  cantidad: number;
  cantidad_pdu: number;
  cantidad_rack: number;
}

export interface Entradas {
  dolar: number;
  numero_propuesta: number | null;
  fecha: string | null;
  cliente: string;
  provincia: string;
  categoria: string;
  distribuidora: string;
  tarifa: string;
  potencia_contratada_kw: number;
  horario_trabajo: string;
  horas_por_dia: number;
  m2_disponibles: number | null;
  origen_m2: string | null;
  costo_mayorista: number;
  tasa_mayorista: number;
  costo_cammesa: number;
  tasa_cammesa: number;
  potencia_contratada_cammesa_kw: number | null;
  costo_distribuidora: number;
  tasas_mun_prov: number;
  tasa_976: number;
  res281_usd_mwh: number;
  retribucion_inyeccion: number;
  tipo_inversor: string;
  inhibicion_inyeccion: boolean;
  banco_capacitores: boolean;
  instalacion: string;
  acimut: number;
  inclinacion: number;
  inversor: string;
  kit1: Kit;
  kit2: Kit | null;
  baterias: Baterias;
  k_incertidumbre: number;
  comision: number;
  tasa_descuento: number;
  periodo_evaluacion: number;
  capacitores: { kvar: number; inversion_usd: number; ahorro_ars_anio: number };
  financiacion: {
    porcentaje: number;
    tipo: string;
    moneda: string;
    plazo_anios: number;
    gracia_anios: number;
    tasa: number;
    gastos_adm: number;
  };
  ppa: {
    aplica: boolean;
    periodo_contrato: number;
    precio_usd_mwh: number;
    inflacion_usd: number;
    fee_salida_usd: number;
    oem: number;
  };
  consumos: ConsumoMensual[];
}

export interface Alerta {
  codigo: string;
  nivel: "error" | "advertencia";
  mensaje: string;
  campo: string | null;
}

export interface Mensual {
  mes: string;
  consumo_kwh: number;
  generacion_kwh: number;
  inyeccion_kwh: number;
}

export interface Resultado {
  kwp_total: number;
  superficie_m2: number;
  mensual: Mensual[];
  energia: {
    consumo_anual_kwh: number;
    generacion_anual_kwh: number;
    inyeccion_anual_kwh: number;
    inyectada_kwh: number;
    desperdiciada_kwh: number;
    autoconsumo_kwh: number;
    cobertura: number;
    autoconsumo_pct: number;
    ahorro_pct: number;
  };
  economia: { precio_kwh_ars: number; precio_kwh_usd: number; ahorro_anual_ars: number; ahorro_anual_usd: number };
  inversion: { total_usd: number; paneles_usd: number; baterias_usd: number; cable_usd: number; capacitores_usd: number };
  roi_anios: number | null;
  curva_roi: number[];
  anios_curva_roi: number;
  van_tir: { van: number; tir: number | null; van_por_periodo: Record<string, number> };
  ppa: { tir: number | null; ventas_anio1_usd: number };
  financiacion: { monto_financiado: number; canon_anual: number; pagos: number[]; ahorros: number[] };
  huella: { tco2_anio: number; tco2_25_anios: number; arboles: number; autos: number };
  capacidad_bateria_recomendada_kwh: number;
  potencia_sugerida_kw: number;
  alertas: Alerta[];
}

export interface Opcion {
  kit1: Kit;
  kit2: Kit | null;
  recomendada: boolean;
  resultado: Resultado;
}

export interface ResultadoBusqueda {
  opciones: Opcion[];
  limitado_por_potencia: boolean;
  evaluadas: number;
  validas: number;
  descartes: Record<string, number>;
}

export interface CampoConfianza<T> {
  valor: T | null;
  confianza: number;
}

export interface FacturaExtraida {
  tipo_documento: string;
  distribuidora: CampoConfianza<string>;
  cliente_razon_social: CampoConfianza<string>;
  cliente_cuit: CampoConfianza<string>;
  domicilio_suministro: CampoConfianza<string>;
  provincia: CampoConfianza<string>;
  tarifa: CampoConfianza<string>;
  periodo_anio: CampoConfianza<number>;
  periodo_mes: CampoConfianza<number>;
  potencia_contratada_pico_kw: CampoConfianza<number>;
  potencia_contratada_fuera_pico_kw: CampoConfianza<number>;
  kwh_total: CampoConfianza<number>;
  importe_basico_energia: CampoConfianza<number>;
  importe_energia_activa: CampoConfianza<number>;
  precio_kwh_resto: CampoConfianza<number>;
  cargo_factor_potencia: boolean;
  importe_total: CampoConfianza<number>;
  energia_reactiva_kvarh: CampoConfianza<number>;
  notas: string;
  [campo: string]: unknown;
}

export interface Sugerencias {
  cliente: string | null;
  cuit: string | null;
  provincia: string | null;
  distribuidora: string | null;
  tarifa: string | null;
  potencia_contratada_kw: number | null;
  potencias_contratadas: (number | null)[];
  costo_distribuidora: number | null;
  costo_distribuidora_origen: "resto" | "energia_activa" | null;
  costo_energia_activa: number | null;
  costo_monomico: number | null;
  cargo_factor_potencia: boolean;
  kvar_sugeridos: number | null;
  tasas_mun_prov: number | null;
  energia_reactiva_kvarh: number | null;
  consumos: (ConsumoMensual | null)[];
  campos_dudosos: string[];
  meses_sin_franjas: number[];
}

export interface RespuestaExtraccion {
  facturas: { archivo: string; datos: FacturaExtraida }[];
  sugerencias: Sugerencias;
}

export interface DiapositivaPpt {
  numero: number;
  titulo: string;
  condicion: string | null;
  nota: string;
}

/** Kits de una opción de la lista, tal como los espera el exporte de PowerPoint. */
export interface KitsOpcion {
  kit1: Kit;
  kit2: Kit | null;
}

export interface OpcionesFormulario {
  diapositivas: DiapositivaPpt[];
  provincias: string[];
  acimuts: number[];
  inclinaciones: number[];
  horas_por_dia: number[];
  periodos_evaluacion: number[];
  categorias: string[];
  horarios: string[];
  tipos_inversor: string[];
  instalaciones: string[];
  inversores: string[];
  objetivos_baterias: string[];
  tipos_financiacion: string[];
  monedas: string[];
  origenes_superficie: string[];
  kits: { kwp: number }[];
  baterias: { modelo: string; kwh: number; min_baterias: number | null; max_baterias: number | null }[];
}
