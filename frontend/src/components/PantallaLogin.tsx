"use client";

import { useState, type FormEvent } from "react";
import { Aviso, Boton } from "@/components/ui";
import { api, ErrorApi } from "@/lib/api";

/** Pide la contraseña de acceso cuando la API está protegida (ver backend/api/acceso.py). */
export function PantallaLogin({ alEntrar }: { alEntrar: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (ev: FormEvent) => {
    ev.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await api.login(password);
      alEntrar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo iniciar sesión");
      setEnviando(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-4 py-8">
      <p className="text-xs font-medium uppercase tracking-wide text-acento">Dynamic Energy</p>
      <h1 className="mb-6 text-2xl font-semibold text-tinta">Estudio de prefactibilidad solar</h1>
      <form onSubmit={enviar} className="flex flex-col gap-4 rounded-lg border border-borde bg-superficie p-5">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-tinta-2">Contraseña de acceso</span>
          <input
            type="password"
            autoFocus
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-borde bg-plano px-3 py-2 text-sm text-tinta outline-none focus:border-acento focus:ring-2 focus:ring-acento/30"
          />
        </label>
        {error && <Aviso nivel="error">{error}</Aviso>}
        <Boton tipo="submit" cargando={enviando} deshabilitado={!password}>
          Entrar
        </Boton>
      </form>
    </div>
  );
}
