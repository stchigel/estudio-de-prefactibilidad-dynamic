"""Entradas y resultados del motor (§6.1).

Los valores de los enums son los textos exactos de las listas de la planilla
(TRANSP), para poder exportarlos al Excel sin traducción.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Categoria(StrEnum):
    INDUSTRIAL = "Industrial < 300kW"
    GUDI = "GUDI"
    GUME = "GUME"


class HorarioTrabajo(StrEnum):
    SIETE_X_24 = "7 x 24"
    LU_A_VI = "Lu a Vi"
    LU_A_SA = "Lu a Sa"
    LU_A_MEDIO_SA = "Lu a 1/2 Sab"


class TipoInversor(StrEnum):
    ON_GRID = "ON GRID"
    HIBRIDO = "HIBRIDO"


class Instalacion(StrEnum):
    COPLANAR = "Coplanar"
    ENGRAFADO = "Engrafado"
    LOSA = "Losa"
    PISO = "Piso"


class Inversor(StrEnum):
    GROWATT = "Growatt"
    HUAWEI = "Huawei"
    DEYE_HIB = "Deye Hib"


class ObjetivoBaterias(StrEnum):
    NINGUNO = "--"
    AHORRO = "Ahorro"
    CORTES = "Cortes"


class TipoFinanciacion(StrEnum):
    LEASING = "Leasing"
    PRESTAMO = "Prestamo"


class Moneda(StrEnum):
    PESOS = "$ ar"
    DOLARES = "U$D"


class OrigenConsumo(StrEnum):
    FACTURA = "factura"
    HISTORIAL = "historial"
    ESTIMADO = "estimado"
    MANUAL = "manual"


class OrigenSuperficie(StrEnum):
    CLIENTE = "informado por cliente"
    DYNAMIC = "relevado por Dynamic"


HORAS_POR_DIA = (8, 9, 10, 12, 24)
PERIODOS_EVALUACION = (5, 6, 7, 8, 9, 10, 15, 25)


@dataclass
class ConsumoMensual:
    valle: float
    resto: float
    pico: float
    origen: OrigenConsumo = OrigenConsumo.MANUAL

    @property
    def total(self) -> float:
        return self.valle + self.resto + self.pico


@dataclass
class Kit:
    kwp: float
    cantidad: int = 1
    distancia_tgbt_m: float = 0.0


@dataclass
class Baterias:
    incluye: bool = False
    objetivo: ObjetivoBaterias = ObjetivoBaterias.NINGUNO
    autonomia_h: float = 0.0
    modelo: str | None = None
    cantidad: int = 0
    cantidad_pdu: int = 0
    cantidad_rack: int = 0


@dataclass
class Capacitores:
    kvar: float = 0.0
    inversion_usd: float = 0.0
    ahorro_ars_anio: float = 0.0


@dataclass
class Financiacion:
    porcentaje: float = 0.0
    tipo: TipoFinanciacion = TipoFinanciacion.PRESTAMO
    moneda: Moneda = Moneda.DOLARES
    plazo_anios: int = 0  # total, gracia incluida (5 con 1 de gracia = 4 de amortización)
    gracia_anios: int = 0  # años de solo intereses
    tasa: float = 0.0
    gastos_adm: float = 0.0


@dataclass
class PPA:
    aplica: bool = False
    periodo_contrato: int = 7
    precio_usd_mwh: float = 0.0
    inflacion_usd: float = 0.0
    fee_salida_usd: float = 0.0
    oem: float = 0.0


@dataclass
class Entradas:
    # Propuesta
    dolar: float
    numero_propuesta: int | None = None
    fecha: date | None = None
    # Cliente
    cliente: str = ""
    provincia: str = "Buenos Aires"
    categoria: Categoria = Categoria.INDUSTRIAL
    distribuidora: str = ""
    tarifa: str = ""
    potencia_contratada_kw: float = 0.0
    horario_trabajo: HorarioTrabajo = HorarioTrabajo.LU_A_VI
    horas_por_dia: int = 8
    m2_disponibles: float | None = None
    origen_m2: OrigenSuperficie | None = None
    # Costos de energía
    costo_mayorista: float = 0.0
    tasa_mayorista: float = 0.0
    costo_cammesa: float = 0.0
    tasa_cammesa: float = 0.0
    potencia_contratada_cammesa_kw: float | None = None  # Hoja1!R9, sin efecto en cálculos (A5)
    costo_distribuidora: float = 0.0
    tasas_mun_prov: float = 0.0
    tasa_976: float = 0.0  # solo GUDI
    res281_usd_mwh: float = 0.0
    retribucion_inyeccion: float = 0.0
    # Sistema
    tipo_inversor: TipoInversor = TipoInversor.ON_GRID
    inhibicion_inyeccion: bool = True
    banco_capacitores: bool = False
    instalacion: Instalacion = Instalacion.COPLANAR
    acimut: int = 0
    inclinacion: int = 15
    inversor: Inversor = Inversor.GROWATT
    kit1: Kit = field(default_factory=lambda: Kit(kwp=11.02))
    kit2: Kit | None = None
    baterias: Baterias = field(default_factory=Baterias)
    # Ajustes
    k_incertidumbre: float = 0.0
    comision: float = 0.0
    # Evaluación
    tasa_descuento: float = 0.12
    periodo_evaluacion: int = 25
    capacitores: Capacitores = field(default_factory=Capacitores)
    financiacion: Financiacion = field(default_factory=Financiacion)
    ppa: PPA = field(default_factory=PPA)
    consumos: list[ConsumoMensual] = field(default_factory=list)

    @property
    def kits(self) -> list[Kit]:
        return [k for k in (self.kit1, self.kit2) if k is not None and k.cantidad > 0]

    @property
    def kwp_total(self) -> float:
        return sum(k.kwp * k.cantidad for k in self.kits)

    @property
    def baterias_activas(self) -> bool:
        """Baterías solo cuentan con inversor híbrido (§6.2, §6.10 #4)."""
        return (
            self.tipo_inversor == TipoInversor.HIBRIDO
            and self.baterias.incluye
            and self.baterias.modelo is not None
        )

    @property
    def tasa_976_aplicable(self) -> float:
        return self.tasa_976 if self.categoria == Categoria.GUDI else 0.0


# ---------------------------------------------------------------- resultados


@dataclass
class Alerta:
    codigo: str
    nivel: str  # "error" | "advertencia"
    mensaje: str
    campo: str | None = None


@dataclass
class Mensual:
    """Detalle mensual (PERFIL DE CONSUMO y BAT)."""

    mes: str
    consumo_kwh: float
    generacion_kwh: float
    hsp: float
    coeficiente: float
    dias_laborables: float
    dias_no_laborables: float
    kw_fuera_horario: float
    kw_horario_laboral: float
    excedente_no_laborable_kwh: float
    excedente_laborable_kwh: float
    inyeccion_kwh: float


@dataclass
class Energia:
    consumo_anual_kwh: float
    generacion_anual_kwh: float
    inyeccion_anual_kwh: float  # excedente total (inyectado o desperdiciado)
    inyectada_kwh: float  # retribuida (inhibición = NO)
    desperdiciada_kwh: float  # inhibición = SI
    autoconsumo_kwh: float
    cobertura: float
    autoconsumo_pct: float
    ahorro_pct: float


@dataclass
class Economia:
    precio_kwh_ars: float
    precio_kwh_usd: float
    ahorro_autoconsumo_ars: float
    ahorro_inyeccion_ars: float
    ahorro_capacitores_ars: float
    ahorro_baterias_ars: float
    ahorro_anual_ars: float
    ahorro_anual_usd: float


@dataclass
class Inversion:
    precio_kwp_kit1: float
    precio_kwp_kit2: float
    paneles_usd: float
    cable_usd: float
    capacitores_usd: float
    baterias_usd: float
    total_usd: float


@dataclass
class VanTir:
    flujos: list[float]  # años 1..25
    van_por_periodo: dict[int, float]
    van: float
    tir: float | None


@dataclass
class ResultadoPPA:
    flujos: list[float]
    van_por_periodo: dict[int, float]
    tir_por_periodo: dict[int, float | None]
    tir: float | None
    ventas_anio1_usd: float


@dataclass
class ResultadoFinanciacion:
    monto_financiado: float
    canon_anual: float
    pagos: list[float]  # años 1..7
    ahorros: list[float]


@dataclass
class Huella:
    tco2_anio: float
    tco2_25_anios: float
    arboles: float
    autos: float


@dataclass
class Resultado:
    kwp_total: float
    superficie_m2: float
    mensual: list[Mensual]
    energia: Energia
    economia: Economia
    inversion: Inversion
    roi_anios: float | None
    curva_roi: list[float]  # capital acumulado, años 1..25
    van_tir: VanTir
    ppa: ResultadoPPA
    financiacion: ResultadoFinanciacion
    huella: Huella
    capacidad_bateria_recomendada_kwh: float
    potencia_sugerida_kw: float
    alertas: list[Alerta]
    version_catalogo: str
    version_parametros: str
    anios_curva_roi: int = 15  # años del gráfico de repago (dinámico según el ROI)
