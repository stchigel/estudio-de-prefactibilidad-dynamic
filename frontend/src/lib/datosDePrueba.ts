/**
 * TEMPORAL, solo para pruebas: una extracción de facturas inventada para recorrer el asistente
 * sin llamar a la IA. Se usa desde el botón «Datos de prueba (sin IA)» del paso Facturas.
 * Para quitarlo: borrar este archivo y el botón en PasoFacturas.tsx.
 *
 * Consumos y costos tomados del caso PLECOR de los tests del backend; cliente y CUIT ficticios.
 * Incluye a propósito un dato dudoso (tarifa), un mes sin franjas (noviembre) y meses de cada origen,
 * para ver esos estados en la pantalla de Consumos.
 */
import type { CampoConfianza, ConsumoMensual, FacturaExtraida, OrigenConsumo, RespuestaExtraccion } from "./tipos";

const CONSUMOS: [number, number, number][] = [
  [7548, 26059, 6116],
  [6322, 24041, 5104],
  [8755, 31205, 7373],
  [8021, 33550, 7205],
  [10621, 37129, 8969],
  [11000, 38000, 9000],
  [11000, 38000, 9000],
  [10621, 37129, 8969],
  [8021, 33550, 7205],
  [8755, 31205, 7373],
  [6322, 24041, 5104],
  [4828, 22842, 4252],
];
const MES_SIN_FRANJAS = 11;

const c = <T>(valor: T | null, confianza = 0.95): CampoConfianza<T> => ({ valor, confianza });

function origen(mes: number): OrigenConsumo {
  return mes <= 6 ? "factura" : mes <= 9 ? "historial" : "estimado";
}

function consumos(): ConsumoMensual[] {
  return CONSUMOS.map(([valle, resto, pico], i) =>
    i + 1 === MES_SIN_FRANJAS
      ? { valle: 0, resto: valle + resto + pico, pico: 0, origen: origen(i + 1) }
      : { valle, resto, pico, origen: origen(i + 1) },
  );
}

function factura(mes: number): FacturaExtraida {
  const [valle, resto, pico] = CONSUMOS[mes - 1];
  const kwh = valle + resto + pico;
  return {
    tipo_documento: "factura_distribuidora",
    distribuidora: c("EPE"),
    cliente_razon_social: c("CLIENTE DE PRUEBA S.A."),
    cliente_cuit: c("30-00000000-0"),
    domicilio_suministro: c("Calle Falsa 123 - Rosario"),
    provincia: c("Santa Fe"),
    tarifa: c("T2 b1", 0.5),
    periodo_anio: c(2026),
    periodo_mes: c(mes),
    potencia_contratada_pico_kw: c(200),
    potencia_contratada_fuera_pico_kw: c(280),
    kwh_total: c(kwh),
    importe_basico_energia: c(Math.round(kwh * 146.7743 * 100) / 100),
    importe_energia_activa: c<number>(null),
    precio_kwh_resto: c(146.7743),
    cargo_factor_potencia: false,
    importe_total: c(Math.round(kwh * 146.7743 * 1.42 * 100) / 100),
    energia_reactiva_kvarh: c<number>(null),
    notas: "Datos de prueba generados sin IA.",
  };
}

/** Una factura por archivo subido (para ver el visor) o una sola ficticia si no se subió ninguno. */
export function extraccionDePrueba(archivos: File[]): RespuestaExtraccion {
  const nombres = archivos.length ? archivos.map((a) => a.name) : ["factura-de-prueba.pdf"];
  return {
    facturas: nombres.map((archivo, i) => ({ archivo, datos: factura(((6 - i - 1 + 12) % 12) + 1) })),
    sugerencias: {
      cliente: "CLIENTE DE PRUEBA S.A.",
      cuit: "30-00000000-0",
      provincia: "Santa Fe",
      distribuidora: "EPE",
      tarifa: "T2 b1",
      potencia_contratada_kw: 280,
      potencias_contratadas: [200, 280],
      costo_distribuidora: 146.7743,
      costo_distribuidora_origen: "resto",
      costo_energia_activa: null,
      costo_monomico: null,
      cargo_factor_potencia: false,
      kvar_sugeridos: null,
      tasas_mun_prov: 0.099,
      energia_reactiva_kvarh: null,
      consumos: consumos(),
      campos_dudosos: ["tarifa"],
      meses_sin_franjas: [MES_SIN_FRANJAS],
    },
  };
}
