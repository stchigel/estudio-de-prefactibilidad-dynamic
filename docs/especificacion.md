# Especificación — Sistema de Estudios de Prefactibilidad Solar (Dynamic Energy)

> Versión 0.1 · 06/10/2026 · Estado: borrador para revisión
> Fuente de verdad de cálculo: `PLANILLA DE Estimación Proyecto financiación.xlsx` (con las correcciones de §6.10).
> Referencia de presentación: `ejemplos-prefactibilidad/12961 ARNEG Prefactibilidad SOLAR.pptx` y `Presentación prefactibilidad SOLAR.pptx` (plantilla).

---

## 1. Objetivo

Reemplazar el flujo manual **facturas → Excel → PowerPoint** por una aplicación web interna que:

1. Recibe las facturas de luz del cliente y extrae los datos automáticamente (con IA).
2. Permite revisar y corregir lo extraído.
3. Calcula exactamente lo mismo que el Excel (con las correcciones acordadas).
4. Propone automáticamente opciones de dimensionamiento a partir del catálogo de kits.
5. Muestra resultados en un panel interactivo.
6. Exporta el Excel original completado y genera el PowerPoint de la propuesta.

## 2. Alcance

### Incluido
- Uso **interno** (equipo de Dynamic). Volumen: "bastantes" propuestas por mes.
- Clientes categoría **Industrial < 300 kW, GUDI y GUME**.
- Extracción automática de facturas de **distribuidora** (texto o escaneadas).
- Una sola superficie / tipo de instalación por proyecto (igual que el Excel).
- Opciones formadas **solo** por kits del catálogo o sumas de kits.

### Fuera de alcance (por ahora)
- Residenciales y comercios chicos (se ocultan de la UI aunque estén en el Excel).
- **Extracción de facturas de CAMMESA y generadora (GUME)**: se evaluará cuando haya acceso a un caso real. Mientras tanto, los costos de esos conceptos se cargan como cualquier otro dato del formulario (igual que hoy en el Excel).
- Varias superficies con tipos de instalación distintos.
- Contenido de la diapositiva de financiación bancaria (CFI): se deja como diapositiva opcional con texto editable.
- Acceso de clientes externos.

## 3. Usuarios y flujo

```mermaid
flowchart LR
  A[1. Nueva propuesta] --> B[2. Subir facturas]
  B --> C[3. Extracción IA]
  C --> D[4. Revisión de consumos<br/>tabla 12 meses]
  D --> E[5. Datos del proyecto<br/>formulario]
  E --> F[6. Opciones automáticas<br/>ranking por ROI]
  F --> G[7. Panel de resultados]
  G --> H1[Excel completado]
  G --> H2[PowerPoint]
```

Único rol: **usuario interno**. Un subconjunto de usuarios puede tener permiso de **administración** (catálogo y parámetros, §9).

## 4. Arquitectura propuesta

| Componente | Tecnología sugerida | Responsabilidad |
|---|---|---|
| Frontend | Next.js (React) + ECharts/Recharts | Carga, revisión, formulario, panel |
| Backend | Python + FastAPI | API, orquestación, exportes |
| Motor de cálculo | Librería Python pura (sin dependencias de web) | Réplica del Excel, testeable aislada |
| Extracción | LLM multimodal con salida estructurada (JSON Schema) | Lectura de facturas PDF/imagen |
| Exportes | `openpyxl` (Excel), `python-pptx` (PPT) | Rellenar plantillas existentes |
| Persistencia | PostgreSQL + almacenamiento de archivos | Propuestas, facturas, catálogo versionado |
| Autenticación | SSO corporativo (Google / Microsoft) | Solo usuarios del dominio de Dynamic |

Consideración de privacidad: las facturas contienen CUIT y domicilios. Usar un proveedor de IA cuyos términos excluyan el uso de datos para entrenamiento.

---

## 5. Módulo de facturas

### 5.1 Carga
- Arrastrar y soltar múltiples archivos (PDF, JPG, PNG). Fotos de celular incluidas.
- Cada archivo queda asociado a la propuesta y se conserva para auditoría.

### 5.2 Extracción (por factura)
El LLM recibe el documento (texto si existe; imagen si es escaneo) y devuelve:

| Campo | Ejemplo (EPE Santa Fe) | Uso |
|---|---|---|
| `distribuidora` | EPE Santa Fe | Hoja1!E7 |
| `cliente_razon_social` | SCIMACA S R L | Hoja1!D5 |
| `cliente_cuit` | 30-58921142-8 | Registro |
| `domicilio_suministro` | Callao 6002, Rosario | Registro |
| `provincia` | Santa Fe | Hoja1!L5 (sugerido) |
| `tarifa` | B1 | Hoja1!I7 |
| `periodo` (mes/año) | 07/2026 | Clave de consolidación |
| `dias_facturados` | 31 | Normalización |
| `potencia_contratada_pico_kw` / `fuera_pico_kw` | 80 / 120 | Hoja1!L7 (se usa la mayor, a confirmar en revisión) |
| `kwh_pico` / `kwh_resto` / `kwh_valle` | 2.746 / 15.151 / 1.850 | Tabla de consumos |
| `kwh_total` | 19.747 | Control |
| `kw_registrados_pico` / `fuera_pico` | 52 / 177 | Informativo |
| `importe_basico_energia` | 8.565.172,32 | Cálculo $/kWh |
| `impuestos[]` (nombre, %, base) | Ley 7797 6% … | Hoja1!I11 (tasas mun/prov) |
| `importe_total` | 12.960.728,37 | Control |
| `energia_reactiva_kvarh` | 3.619,8 | Banco de capacitores |
| `historial[]` (período, kWh por franja, kW) | 6 meses | Completar meses faltantes |
| `confianza` por campo | 0–1 | Resaltado en revisión |

Notas por formato observado:
- **EPE**: trae historial de 6 meses con franjas → 2 facturas cubren el año.
- **CEB**: trae gráfico de 12 meses (sin valores por mes en texto) + promedio anual.
- **Edenor**: PDF escaneado sin capa de texto → requiere lectura por imagen.

### 5.3 Consolidación a 12 meses
1. Se unifican todos los meses (factura propia + historiales). Ante duplicados prevalece el dato de la factura del propio período.
2. Los meses faltantes se completan **espejando** respecto del solsticio, igual que el Excel: FEB←NOV, MAR←OCT, ABR←SEP, MAY←AGO, JUN←JUL (y viceversa).
3. Todo valor estimado se marca visualmente como **"estimado"**.

### 5.4 Datos derivados de la factura
- **Costo distribuidora $/kWh** (Hoja1!E11) = **precio unitario del kWh en la franja resto** de la factura (promedio ponderado por kWh de resto). NO se usa el monómico (importe básico ÷ kWh), que incluye cargos fijos y de potencia que la solar no reduce. Si la factura no trae el precio en resto, se cae a energía activa ÷ kWh (se avisa en el formulario). Editable.
- **Banco de capacitores**: si la factura trae un cargo por factor de potencia (`cargo_factor_potencia`), el formulario activa el banco y precarga los kVAr (Bco Capac: Qc = P·(tan φ − tan φ_obj), P = potencia contratada, cos φ objetivo 0,95). Inversión y ahorro se completan a mano.
- **Tasas mun/prov** (Hoja1!I11) = suma de % de impuestos provinciales/municipales sobre subtotal. Editable.

### 5.5 Pantalla de revisión
- Visor del PDF a la izquierda, datos extraídos a la derecha.
- Campos con baja confianza resaltados.
- Tabla editable de 12 meses × (valle, resto, pico, total) con indicador de origen: *factura*, *historial*, *estimado*, *manual*.
- Botón "confirmar consumos" para avanzar.

---

## 6. Motor de cálculo

Réplica de las hojas `Hoja1`, `PERFIL DE CONSUMO`, `BAT`, `ROI`, `VAN TIR`, `Financiación`, `Bco Capac`. Las referencias a celdas sirven para trazabilidad y para los tests de equivalencia.

### 6.1 Entradas (formulario)

| Grupo | Campo | Celda Excel | Tipo / opciones |
|---|---|---|---|
| Propuesta | N° propuesta | K3 | Autonumérico |
| | Fecha | M3 | Fecha |
| | Valor dólar $/U$D | R3 | Número |
| Cliente | Nombre | D5 | Texto |
| | Provincia | L5 | Lista: 24 provincias (TRANSP!U1:AR1) |
| | Categoría | O5 | Industrial < 300kW · GUDI · GUME |
| | Distribuidora | E7 | Texto |
| | Tarifa | I7 | Texto |
| | Potencia contratada kW | L7 | Número |
| | Horario de trabajo | O7 | 7 x 24 · Lu a Vi · Lu a Sa · Lu a 1/2 Sab |
| | Horas por día | R7 | 8 · 9 · 10 · 12 · 24 |
| | **m² disponibles** | *(nuevo)* | Número + origen: *informado por cliente* / *relevado por Dynamic* |
| Costos energía | Costo mayorista $/kWh + tasas | E9, H9 | Número, % |
| | Costo CAMMESA $/kWh + tasas | L9, O9 | Número, % |
| | Costo distribuidora $/kWh + tasas mun/prov | E11, I11 | Número, % (sugerido de factura) |
| | Tasa Res. 976/23 promedio | M11 | % — **visible solo si GUDI** |
| | Res. 976/281 U$D/MWh (etiqueta en pantalla) | R11 | Número |
| | Retribución por inyección $/kWh | F13 | Número |
| Sistema | Tipo inversor | E15 | ON GRID · HIBRIDO |
| | Inhibición de inyección | K15 | SI · NO |
| | Banco de capacitores | O15 | SI · NO |
| | Tipo de instalación | D18 | Coplanar · Engrafado · Losa · Piso |
| | Acimut | H18 | 0 · 15 · 30 · 45 · 60 |
| | Inclinación | K18 | 5 · 10 · 15 · 20 · 25 · 30 · 35 · 40 |
| | Inversor | N18 | Growatt · Huawei · Deye Hib |
| | Kit 1 kWp × cantidad | E20, G20 | Catálogo (§9.1) × entero |
| | Distancia inversor–TGBT kit 1 (m) | O20 | Número |
| | Kit 2 kWp × cantidad | E22, G22 | Catálogo × entero (0 = sin kit 2) |
| | Distancia inversor–TGBT kit 2 (m) | O22 | Número |
| Baterías | Incluye baterías | D24 | SI · NO |
| | Objetivo | F24 | -- · Ahorro · Cortes |
| | Autonomía (h) | I24 | Número — **visible solo si Cortes** |
| | Modelo | E26 | Catálogo de baterías (§9.1) |
| | Cantidad baterías / PDU / Rack | J26, O26, G28 | Enteros (validados, §6.2) |
| Ajustes | K incertidumbre % | O28 | % |
| | Comisión / gastos % | R28 | % |
| Evaluación | Tasa de descuento | I31 | % |
| | Período de evaluación (años) | N31 | 5 · 6 · 7 · 8 · 9 · 10 · 15 · 25 |
| Capacitores | kVAr · inversión U$D · ahorro $/año | G40, L40, P40 | Números — **visible solo si banco = SI** |
| Financiación | % a financiar | F44 | % |
| | Tipo | H44 | Leasing · Préstamo |
| | Moneda | K44 | $ar · U$D |
| | Plazo (años) · gracia (años) | N44, Q44 | Enteros |
| | Tasa % · gastos adm. % | E46, F46 | % |
| PPA | Aplica PPA | J49 | SI · NO |
| | Período contrato (años) | F51 | 5 · 6 · 7 · 8 · 9 · 10 · 15 · 25 |
| | Precio venta U$D/MWh | L51 | Número |
| | Inflación anual U$D | R51 | % |
| | Fee de salida U$D · OE&M % | J53, M53 | Número, % |
| Consumos | Valle / Resto / Pico por mes | W7:Y18 | Desde §5.3 |

### 6.2 Validaciones (reemplazan el "OK/ERROR" del Excel)
- Si tipo de inversor = **ON GRID** → "incluye baterías" queda bloqueado en **NO** y se ocultan los campos de baterías.
- Si **incluye baterías = SI** → inversor debe ser **Deye Hib** y tipo **HIBRIDO** (Hoja1!Q24).
- Cantidad de baterías dentro del mínimo/máximo del modelo (ej. HV 16 kWh: mín 5, máx 16; HV 7,68 kWh: mín 7).
- PDU: 1 cada N baterías según modelo (16 o 21); rack con máximo por modelo (13 o 16). Se sugieren automáticamente.
- Potencia sugerida mayor a la contratada → advertencia (PERFIL!I7:I16).
- Superficie requerida > m² disponibles → advertencia / exclusión en búsqueda de opciones.

### 6.3 Generación
Para cada mes *m* (días: 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31):

```
kWp_total   = kit1.kWp × cant1 + kit2.kWp × cant2
HSP[m]      = tabla HSP por provincia (TRANSP!U1:AR13)
coef[m]     = tabla coeficientes por (acimut, inclinación, provincia, mes) (TRANSP!A:O)
Gen[m]      = kWp_total × HSP[m] × coef[m] × días[m]
Gen_anual   = Σ Gen[m]
```

### 6.4 Autoconsumo e inyección (modelo horario, hoja BAT)
Para cada mes *m*, con semanas[m] = 4,4,5,4,4,5,4,4,5,4,4,5:

```
días_lab[m]   = 7x24: días | Lu a Vi: días − 2·sem | Lu a Sa: días − sem | Lu a 1/2 Sab: días − 1,5·sem
días_nolab[m] = días − días_lab
h             = min(horas_por_día, 11)
kW_fuera[m]   = valle[m] / días[m] / 6
kW_lab[m]     = si días_lab = 0: resto / (días_nolab · 11)
                si no:          (resto − kW_fuera · días_nolab · h) / (días_lab · h)
gen_h[m,t]    = perfil_horario[m,t] × (Gen[m] / días[m])         t = 7:00 … 19:00 (13 franjas)
exc_nolab[m]  = Σ_t max(gen_h − kW_fuera, 0)    (0 si días_nolab = 0)
exc_lab[m]    = Σ_t max(gen_h − kW_lab, 0)
cap_bat       = baterías = SI ? kWh_por_batería × cantidad : 0
Iny[m]        = max(exc_nolab − cap_bat, 0) · días_nolab + max(exc_lab − cap_bat, 0) · días_lab
Iny_anual     = Σ Iny[m]
```
- `perfil_horario` es una tabla de 12 × 13 fracciones (BAT!AA20:AM31) → parámetro administrable.
- Si inhibición = SI → `Iny_anual` se considera **desperdiciada**; si NO → **inyectada** y retribuida.

### 6.5 Indicadores energéticos
```
Consumo_anual = Σ (valle + resto + pico)
Autoconsumo   = Gen_anual − Iny_anual
Cobertura %   = Gen_anual / Consumo_anual
Autoconsumo % = Autoconsumo / Gen_anual
Ahorro %      = (Autoconsumo + Inyectada) / Consumo_anual
```

### 6.6 Precio de la energía y ahorro
```
P_kWh ($) = mayorista·(1+tasa_may) + CAMMESA·(1+tasa_cam)
          + distribuidora·(1+tasas_mun_prov)·(1+tasa_976)
          + Res281_USD_MWh · dólar / 1000
P_kWh_USD = P_kWh / dólar                                  (corrección §6.10: sin R21)

Ahorro_$  = Autoconsumo · P_kWh
          + (inhibición = NO ? Iny_anual · retribución : 0)
          + (capacitores = SI ? ahorro_capacitores : 0)
Ahorro_USD = Ahorro_$ / dólar
```

### 6.7 Inversión
```
P_kWp(kit, instalación, inversor) = precio_base[kit][instalación] + adicional_inversor[kit][inversor]
Cable_i   = dist_i < 5 ? 0 : (dist_i − 5) · USD_por_m[kit_i] · cant_i
Baterías  = (ON GRID o sin baterías) ? 0
          : precio_bat · cant_bat + precio_PDU · cant_PDU + precio_rack · cant_rack
Inversión = ( Σ_i kWp_i · P_kWp_i · cant_i + Σ Cable_i
            + (capacitores = SI ? inversión_capacitores : 0) + Baterías )
            · (1 + K_incertidumbre) / (1 − comisión)
```

### 6.8 Superficie (corregida)
```
Superficie_m2 = kWp_total / 0,58 × factor
factor: Coplanar = 2,9 · Engrafado = 2,9 · Losa = 3,5 · Piso = 5
```

### 6.9 Indicadores financieros

**ROI (repago)** — solo la tabla sin inflación (ROI!A2:D17):
```
Capital[1] = Ahorro_USD − Inversión ;  Capital[k] = Capital[k−1] + Ahorro_USD
ROI_años   = interpolación lineal del cruce por cero  (≡ Inversión / Ahorro_USD)
Gráfico    = años 1 .. min(25, max(8, ⌈ROI⌉ + 5))   (dinámico según el caso; 15 si no hay repago)
```

**VAN / TIR** — tal como está en el Excel (confirmado):
```
Ingreso[1] = Ahorro_USD ; Ingreso[2] = Ingreso[1]·0,99 ; Ingreso[k≥3] = Ingreso[k−1]·0,994
CAPEX[1]   = Inversión ; si PPA = SI: CAPEX[N] = −fee_salida en el año N = período de evaluación
Flujo[k]   = Ingreso[k] − CAPEX[k]          k = 1..25
VAN(N)     = NPV(tasa_descuento, Flujo[1..N])      N ∈ {5,6,7,8,9,10,15,25}
TIR        = IRR(Flujo[1..25])
```

**PPA** (VAN TIR!A30:S33):
```
Energía[1]  = (Autoconsumo + Inyectada) · (1 − OE&M) ; Energía[2] = ·0,99 ; Energía[k≥3] = ·0,994
Precio[1]   = precio_MWh / 1000 ; Precio[k] = Precio[k−1] · (1 + inflación_USD)
Ventas[k]   = Energía[k] · Precio[k]
Flujo[k]    = Ventas[k] − CAPEX[k]   (fee de salida en año = período de contrato)
TIR_PPA     = IRR(Flujo[1..período_contrato])
Ventas_año1 = precio_MWh · Autoconsumo / 1000
```

**Financiación** (7 años de gráfico; el plazo es el **total**, gracia incluida):
```
Financiado = Inversión · %financiar ;  i = tasa + gastos_adm ;  r = i / 12
Amortiza   = plazo − gracia                      (5 con 1 de gracia = 1 de solo intereses + 4 de capital)
Canon      = 12 · Financiado · r / (1 − (1 + r)^(−12·Amortiza))      (sin capitalizar la gracia)
Pago[k]    = k ≤ gracia ? Financiado · i : (k ≤ plazo ? Canon : 0)
Pago[1]   += Inversión − Financiado              (anticipo)
Ahorro[k]  = Ahorro_USD (constante, k = 1..7)
```

**Huella de carbono**:
```
tCO2_año = Gen_anual · 0,35 / 1000 ;  tCO2_25 = tCO2_año · 25
Árboles  = Gen_anual · 16,6 / 1000 ;  Autos   = Gen_anual · 0,15 / 1000
```

**Banco de capacitores** (hoja Bco Capac):
```
cosφ = E_activa / √(E_activa² + E_reactiva²) ;  φ_obj = acos(0,95)
Qc_kVAr = P · (tan φ − tan φ_obj)
```

**Capacidad de batería recomendada**:
- Objetivo *Ahorro* → máximo excedente diario de día laboral (max `exc_lab[m]`).
- Objetivo *Cortes* → promedio `kW_lab` × autonomía (h).

### 6.10 Diferencias intencionales respecto del Excel actual
| # | Excel | Sistema | Motivo |
|---|---|---|---|
| 1 | `PERFIL DE CONSUMO!R33 = R20·(1+R21)/T28` (R21 vacía) | `P_kWh / dólar` | Confirmado: ignorar R21 |
| 2 | Superficie Engrafado usa factor 5 | Factor 2,9 (igual a Coplanar) | Confirmado |
| 3 | Hoja ROI tiene tabla con inflación 6 % (M:P) | No se usa | Confirmado: solo tabla sin inflación |
| 4 | La capacidad de baterías reduce la inyección aunque sea ON GRID / baterías = NO | En la UI no se puede combinar ON GRID con baterías; sin baterías `cap_bat = 0` | Confirmado |

| 5 | Planilla: `N44` = años de amortización, la gracia se suma aparte | El plazo es el total (gracia incluida) | Pedido de prefactibilidad. Al exportar se escribe `N44 = plazo − gracia` |
| 6 | Planilla capitaliza la gracia (`Financiado·(1 + gracia·i)`) | Gracia = solo intereses, sin capitalizar | Pedido de prefactibilidad. Con gracia > 0 el Excel exportado da otros pagos |

Se recomienda aplicar también #2 en la planilla para que el Excel exportado coincida con el sistema.

---

## 7. Búsqueda automática de opciones

1. Generar todas las combinaciones `kit_a × n_a (+ kit_b × n_b)` del catálogo.
2. Descartar las que:
   - superen los m² disponibles (si fueron informados);
   - superen la potencia contratada (con aviso "limitado por la potencia contratada" si es la restricción activa);
   - generen excedente inyectado desproporcionado con inhibición = SI (umbral configurable).
3. Calcular cada combinación con el motor completo.
4. Ordenar por **ROI** (menor = mejor). Desempate: mayor cobertura cuando la diferencia de ROI < 0,2 años (configurable).
5. Presentar la **recomendada** (mejor ROI) más **2 tamaños más chicos y 2 más grandes** en potencia (separados al menos 15 % entre sí; si de un lado no alcanzan, se completan con el otro). Combinaciones de potencia similar (±5 %) son el mismo tamaño: si la segunda tiene ROI a menos de 0,2 años de la mejor, se muestran **las dos** (p. ej. 2 × 55 kWp y 1 × 110 kWp).
6. Los kits armados a mano se **agregan a la tabla** (no reemplazan la búsqueda) y se pueden elegir como la preferida. Cada opción tiene un tilde «En el PPT»; las destildadas se ven atenuadas: las tildadas forman la tabla de opciones de la presentación (la elegida va siempre). El usuario puede **elegir otra manualmente** o editar una opción. La opción elegida alimenta las diapositivas de "los números", ROI y financiación.

---

## 8. Panel de resultados

- **KPIs**: potencia, inversión, generación, cobertura, autoconsumo, superficie (vs. disponible), ahorro anual, ROI, TIR, VAN.
- **Gráficos**: consumo vs. generación mensual; curva de ROI (capital acumulado); cash flow de financiación **semestral** (pagos y ahorros en barras, ahorro acumulado en línea, 7 años); comparación de opciones.
- **Sensibilidad rápida**: dólar, tasa de descuento, inhibición, baterías → recálculo inmediato.
- **Alertas**: superficie insuficiente, potencia sobre contratada, meses estimados, validaciones de baterías.

---

## 9. Administración (catálogo y parámetros)

Todo versionado con fecha de vigencia; cada propuesta registra la versión usada.

### 9.1 Catálogo
- **Kits** (TRANSP!Y19:AG28): kWp (11,02 · 16,24 · 22,04 · 27,84 · 33,64 · 44,08 · 55,68 · 88,16 · 110,2 · 139,02), precio U$D/kWp por instalación (Coplanar, Engrafado, Losa, Piso), adicional por inversor (Growatt, Huawei, Deye Hib), cable CA U$D/m.
- **Baterías** (TRANSP!T43:Z55): modelo, kWh, precio, PDU (precio, regla 1 cada N), rack (precio, máx.), mín/máx baterías. El factor de margen (hoy `× 1,5`) se guarda como parámetro separado.

### 9.2 Parámetros técnicos
- HSP mensual por provincia (24 × 12).
- Coeficientes por acimut × inclinación × provincia × mes (960 filas × 12).
- Perfil horario solar 12 × 13.
- Factores de superficie por tipo de instalación; factor 0,58.
- Constantes de huella (0,35 · 16,6 · 0,15).
- Degradación (0,99 año 2; 0,994 siguientes).

### 9.3 Contenido fijo de la presentación
- Antecedentes (lista de instalaciones), datos de contacto, textos de beneficios fiscales (RIMI), texto de financiación bancaria.

---

## 10. Exportes

### 10.1 Excel
Se completa una **copia de la planilla original** escribiendo solo las celdas de entrada (§6.1); las fórmulas recalculan al abrir. Sirve como respaldo y control cruzado.

### 10.2 PowerPoint
Se rellena la plantilla preservando el diseño. Mapeo:

| # | Diapositiva | Datos | Condición |
|---|---|---|---|
| 1 | Portada | N° propuesta, fecha, tipo (ON-GRID / HÍBRIDO), logo cliente (imagen) | Siempre |
| 2 | El objetivo | Nombre cliente, foto planta (imagen) | Siempre |
| 3 | La oportunidad detectada | Nombre cliente, **m² disponibles** (+ origen), viñeta "Corrección del factor de potencia", foto montaje | Viñeta FP solo si banco de capacitores = SI. Plantilla con m² pendiente |
| 4 | La solución | Tipo de sistema en título | Siempre |
| 5 | Arquitectura | Cobertura %, autoconsumo %, kWp fase 1, leyenda "limitado por la potencia contratada" | Leyenda solo si aplica |
| 6 | Previsibilidad | — (ilustrativo) | Siempre |
| 7 | **Opciones propuestas** (tabla) | Por opción: tipo, kWp, bat kWh, generación, cobertura, autoconsumo, inversión, ahorro, ROI, TIR, superficie; recomendada marcada | Solo si se presentan varias opciones |
| 8 | Los números | kWp, inversión, generación, autoconsumo, superficie, ahorro, ROI, TIR | Siempre |
| 9 | Retorno | "menos de ⌈ROI⌉ años", año y meses de repago, años de ahorro neto (25 − ROI), **curva ROI como gráfico nativo** | Siempre |
| 10 | Financiamiento propio | Gráfico pagos vs. ahorros 7 años; textos generados desde los parámetros (tasa, plazo, gracia, % financiado) | Si % a financiar > 0 |
| 11 | Financiamiento bancario | Texto editable (ej. CFI) | Opcional |
| 12 | Beneficios fiscales | — | Siempre |
| 13 | Impacto ambiental | tCO₂/año, tCO₂ 25 años, árboles, autos, generación | Siempre |
| 14 | Posicionamiento | — | Siempre |
| 15 | Track record | Desde administración | Siempre |
| 16 | Siguientes pasos | — | Siempre |

Imágenes no generables (logo, foto planta, foto montaje): carga opcional; si faltan, queda el marcador.

**Selector de páginas**: en el panel se puede activar/desactivar cada una de las 16 diapositivas. Las condicionales (7, 10, 11) se omiten solas si no corresponden aunque estén activadas.
**Texto CFI**: el bloque «CFI» de la diapositiva 10 (condiciones de la línea) se completa con un texto editable (una línea por renglón), precargado con el de las presentaciones de ejemplo; vacío = sin bloque.

---

## 11. Datos persistidos

| Entidad | Contenido principal |
|---|---|
| Cliente | Razón social, CUIT, provincia, distribuidora |
| Propuesta | N°, fecha, estado, usuario, versión de catálogo/parámetros |
| Factura | Archivo, tipo, datos extraídos, confianza, correcciones |
| ConsumoMensual | Mes, valle/resto/pico, origen (factura/historial/estimado/manual) |
| Entradas | Snapshot del formulario §6.1 |
| Opción | Combinación de kits, resultados, recomendada/elegida |
| Exporte | Archivos generados (Excel, PPT) con fecha |
| Catálogo / Parámetros | Versionados con vigencia |

---

## 12. Validación del motor

- **Tests de equivalencia** contra el Excel: un conjunto de casos (incluyendo PLECOR, DURALITTE, ARNEG) con entradas conocidas; el motor debe reproducir los resultados del Excel con tolerancia < 0,1 %, salvo las diferencias de §6.10 (que se testean contra el valor corregido).
- Tests de casos borde: 7 x 24, sin días no laborables, kit 2 vacío, gracia 0, sin baterías, inhibición SI/NO.

---

## 13. Etapas

| Etapa | Entregable |
|---|---|
| 1 — MVP | Carga + extracción de distribuidora + revisión + formulario + motor validado + panel (1 opción) + exporte Excel |
| 2 | Búsqueda automática de opciones + generación de PowerPoint |
| 3 | Administración de catálogo/parámetros versionados + historial de propuestas |
| 4 | GUME (con caso real), dólar automático, mejoras de extracción |

---

## 14. Pendientes

### 14.1 Pendientes de contenido / alcance

| # | Tema | Estado |
|---|---|---|
| 1 | Plantilla PPT con m² en "La oportunidad detectada" | El usuario la enviará |
| 2 | Contenido de financiación bancaria (CFI) | Sin definir; diapositiva opcional |
| 3 | Facturas GUME (CAMMESA + generadora) | Fuera de alcance hasta tener un caso real |

### 14.2 Ajustes a futuro del cálculo (consultados al equipo, sin respuesta)

No bloquean el desarrollo. **Hasta que haya respuesta, se implementa el comportamiento indicado** (igual al Excel salvo #A4). Cada uno debe quedar aislado en el motor (una función o parámetro) para poder cambiarlo sin tocar el resto, y cubierto por un test que documente el comportamiento actual.

| # | Tema | Comportamiento provisorio | Posible ajuste futuro |
|---|---|---|---|
| A1 | `Hoja1!J22`: el adicional por inversor del **kit 2** se busca con el kWp del **kit 1** (`MATCH($E$20,…)`) | Replicar el Excel: kit 2 usa el adicional del tamaño del kit 1 | Usar el adicional del tamaño del propio kit 2 |
| A2 | `BAT!N1` solo reconoce baterías High Voltage; Low Voltage → capacidad 0 | Replicar el Excel: Low Voltage con capacidad 0 para el cálculo de inyección (su costo sí se suma) | Usar su capacidad real (5,12 / 16 kWh) o quitarlas del catálogo |
| A3 | Ahorro por baterías: `PERFIL DE CONSUMO!X20` divide por `V30` (vacía) y `T26` suma `V24` (vacía) → nunca se suma | Ahorro por baterías = 0 | Definir fórmula (energía almacenada × precio, pico evitado, cortes) |
| A4 | Potencia contratada (L7) cuando la factura trae pico y fuera de pico distintas | Precargar la **mayor** de las dos, mostrando ambas en la revisión; editable | Regla que defina el equipo (pico / fuera de pico / mayor) |
| A5 | `Hoja1!R9` (Pot Contr kW, bloque CAMMESA) no se usa en fórmulas | Campo opcional, se guarda y se exporta al Excel, sin efecto en cálculos | Eliminarlo o incorporarlo (posiblemente GUME) |
| A6 | **[RESUELTO: se usa el precio en resto, ver §5.4]** Costo distribuidora $/kWh sugerido (§5.4). El "importe básico" incluye cargos fijos y de capacidad contratada, que la solar no reduce. Ej. factura EPE 07/2026: importe básico ÷ kWh = **434 $/kWh**; solo energía activa ÷ kWh = **124 $/kWh** (≈ 3,5× menos ahorro) | Se precarga importe básico ÷ kWh (como dice §5.4) y en la revisión se muestran ambos valores; editable | Precargar solo energía activa ÷ kWh (`importe_energia_activa`, ya se extrae). Cambio en `extraccion/derivados.py → sugerir()` y en `aplicarSugerencias` del frontend |

| A7 | **[PENDIENTE DE ACLARACIÓN]** «Sumar lo que se inyecta como parte del ahorro». El ahorro ya suma inyectada × retribución, pero solo con inhibición = NO y retribución > 0. Falta saber qué se espera ver distinto | Sin cambios | Valorizar la inyección aun con inhibición, precargar la retribución, o mostrar el desglose |

### 14.3 Resueltos

| Tema | Resolución |
|---|---|
| Baterías reducen inyección con ON GRID / baterías = NO | §6.2 y §6.10 #4 |
| A6 · costo distribuidora | Se usa el precio del kWh en resto, no el monómico (§5.4) |
