/** Tema de la interfaz: "sistema" sigue al sistema operativo; "claro" / "oscuro" lo fijan a mano. */
export type Tema = "sistema" | "claro" | "oscuro";

const CLAVE = "prefactibilidad:tema";
const ATRIBUTO: Record<Tema, string | null> = { sistema: null, claro: "light", oscuro: "dark" };

/** Corre antes del primer pintado (en <head>) para que no parpadee el tema guardado. */
export const SCRIPT_TEMA = `(function(){try{var t=localStorage.getItem("${CLAVE}");if(t==="claro")document.documentElement.setAttribute("data-theme","light");else if(t==="oscuro")document.documentElement.setAttribute("data-theme","dark")}catch(e){}})()`;

export function leerTema(): Tema {
  try {
    const t = localStorage.getItem(CLAVE);
    return t === "claro" || t === "oscuro" ? t : "sistema";
  } catch {
    return "sistema";
  }
}

export function aplicarTema(t: Tema): void {
  const valor = ATRIBUTO[t];
  if (valor) document.documentElement.setAttribute("data-theme", valor);
  else document.documentElement.removeAttribute("data-theme");
  try {
    if (t === "sistema") localStorage.removeItem(CLAVE);
    else localStorage.setItem(CLAVE, t);
  } catch {
    /* sin almacenamiento: el tema vale solo para esta sesión */
  }
}
