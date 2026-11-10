import type {
  Alerta,
  Entradas,
  KitsOpcion,
  OpcionesFormulario,
  RespuestaExtraccion,
  Resultado,
  ResultadoBusqueda,
} from "./tipos";

// Por defecto, mismo origen: next.config.ts reenvía /api al backend.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ErrorApi extends Error {
  constructor(
    public estado: number,
    mensaje: string,
    public alertas: Alerta[] = [],
  ) {
    super(mensaje);
  }
}

/** Aviso global de que la sesión se venció o falta: la pantalla principal vuelve a pedir la contraseña. */
export const EVENTO_SESION_VENCIDA = "sesion-vencida";

function sesionVencida() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENTO_SESION_VENCIDA));
}

// La cookie de sesión viaja también cuando la API está en otro origen (frontend estático + API aparte).
const conCredenciales = (init?: RequestInit): RequestInit => ({ ...init, credentials: "include" });

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${BASE}${ruta}`, conCredenciales(init));
  } catch {
    throw new ErrorApi(0, `No se pudo conectar con el servidor (${BASE || "mismo origen"}). ¿Está corriendo el backend?`);
  }
  if (r.status === 401 && ruta !== "/api/login") sesionVencida();
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => ({}));
    const detalle = cuerpo.detail;
    if (Array.isArray(detalle) && detalle[0]?.codigo) {
      throw new ErrorApi(r.status, detalle.map((a: Alerta) => a.mensaje).join(" · "), detalle);
    }
    if (Array.isArray(detalle)) {
      throw new ErrorApi(r.status, detalle.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join(" · "));
    }
    throw new ErrorApi(r.status, typeof detalle === "string" ? detalle : `Error ${r.status}`);
  }
  return r.json();
}

async function descargar(r: Response, nombrePorDefecto: string): Promise<void> {
  const nombre = r.headers.get("content-disposition")?.match(/filename\*?=(?:utf-8'')?"?([^";]+)/i)?.[1] ?? nombrePorDefecto;
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: decodeURIComponent(nombre) });
  a.click();
  URL.revokeObjectURL(url);
}

const json = (cuerpo: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cuerpo),
});

export const api = {
  sesion: () => pedir<{ requiere_login: boolean; autenticado: boolean }>("/api/sesion"),
  login: (password: string) => pedir<{ autenticado: boolean }>("/api/login", json({ password })),
  logout: () => pedir<{ autenticado: boolean }>("/api/logout", { method: "POST" }),
  opciones: () => pedir<OpcionesFormulario>("/api/opciones"),
  calcular: (e: Entradas) => pedir<Resultado>("/api/calcular", json(e)),
  validar: (e: Entradas) => pedir<Alerta[]>("/api/validar", json(e)),
  buscarOpciones: (e: Entradas) => pedir<ResultadoBusqueda>("/api/opciones/buscar", json(e)),
  sugerirBaterias: (modelo: string, cantidad: number) =>
    pedir<{ cantidad_pdu: number; cantidad_rack: number }>("/api/baterias/sugerir", json({ modelo, cantidad })),
  extraerFacturas: (archivos: File[]) => {
    const datos = new FormData();
    archivos.forEach((a) => datos.append("archivos", a));
    return pedir<RespuestaExtraccion>("/api/facturas/extraer", { method: "POST", body: datos });
  },
  async exportarExcel(e: Entradas): Promise<void> {
    const r = await fetch(`${BASE}/api/exportes/excel`, conCredenciales(json(e)));
    if (r.status === 401) sesionVencida();
    if (!r.ok) throw new ErrorApi(r.status, "No se pudo generar el Excel");
    await descargar(r, "propuesta.xlsx");
  },
  async exportarPpt(
    e: Entradas,
    opciones: {
      /** Opciones tildadas para la tabla; null = todas las de la búsqueda. */
      opcionesIncluidas: KitsOpcion[] | null;
      diapositivasExcluidas: number[];
      textoBancario: string;
      textoCfi: string;
      imagenes: Partial<Record<"logo" | "planta" | "montaje", File>>;
    },
  ): Promise<void> {
    const datos = new FormData();
    datos.append(
      "datos",
      JSON.stringify({
        entradas: e,
        opciones_incluidas: opciones.opcionesIncluidas,
        diapositivas_excluidas: opciones.diapositivasExcluidas,
        texto_bancario: opciones.textoBancario || null,
        texto_cfi: opciones.textoCfi || null,
      }),
    );
    for (const [nombre, archivo] of Object.entries(opciones.imagenes)) if (archivo) datos.append(nombre, archivo);
    let r: Response;
    try {
      r = await fetch(`${BASE}/api/exportes/ppt`, conCredenciales({ method: "POST", body: datos }));
    } catch {
      throw new ErrorApi(0, "No se pudo conectar con el servidor");
    }
    if (r.status === 401) sesionVencida();
    if (!r.ok) {
      const cuerpo = await r.json().catch(() => ({}));
      throw new ErrorApi(r.status, typeof cuerpo.detail === "string" ? cuerpo.detail : "No se pudo generar la presentación");
    }
    await descargar(r, "propuesta.pptx");
  },
};
