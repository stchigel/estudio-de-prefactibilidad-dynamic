"use client";

import { useState, type FormEvent } from "react";
import { Aviso, Boton, claseInput, Marca, SelectorTema } from "@/components/ui";
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
    <div className="relative flex flex-1 flex-col">
      <div className="absolute right-4 top-4 sm:right-6">
        <SelectorTema />
      </div>
      <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-4 py-12">
        <Marca />
        <form onSubmit={enviar} className="flex flex-col gap-4 rounded-xl border border-borde bg-superficie p-6">
          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-tinta-2">Contraseña de acceso</span>
            <input
              type="password"
              autoFocus
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={claseInput}
            />
          </label>
          {error && <Aviso nivel="error">{error}</Aviso>}
          <Boton tipo="submit" cargando={enviando} deshabilitado={!password}>
            Entrar
          </Boton>
        </form>
      </main>
    </div>
  );
}
