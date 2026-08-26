# -*- coding: utf-8 -*-
"""
Plantilla 1 - Machine Learning supervisado
Genera el archivo cartera_clientes.csv

QUE ES ESTO
   Una cartera de facturas de una distribuidora que le vende a cadenas, mayoristas,
   tiendas de barrio e instituciones. Cada fila es una factura ya cerrada: sabemos
   si el cliente pago a tiempo o si se atraso. Eso es lo que hace SUPERVISADO el
   problema: los ejemplos ya vienen respondidos.

AVISO IMPORTANTE
   Los datos son SINTETICOS: los inventa este script con una semilla fija, con un
   patron realista, para que la plantilla corra sin descargar nada y sin exponer
   informacion de ninguna empresa. No son datos de Distintores, ni de Supermo, ni
   de la clinica oftalmologica. Cuando usted cambie el CSV por el suyo, el resto
   del pipeline no cambia.

Diplomado en Inteligencia Artificial - UNAC - Clase 05
"""

import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
SEMILLA = 42          # fíjela y todo el salón obtiene los mismos números
FILAS = 4000          # cuántas facturas se inventan
ARCHIVO = "cartera_clientes.csv"
# ---------------------------------------------------------------------------

rng = np.random.default_rng(SEMILLA)

CANALES = ["Cadena", "Mayorista", "Tienda de barrio", "Institucional"]
PESO_CANAL = [0.22, 0.28, 0.36, 0.14]
ZONAS = ["Medellin", "Bogota", "Cali", "Costa", "Eje Cafetero"]
PESO_ZONA = [0.30, 0.26, 0.16, 0.16, 0.12]

canal = rng.choice(CANALES, size=FILAS, p=PESO_CANAL)
zona = rng.choice(ZONAS, size=FILAS, p=PESO_ZONA)

# Antigüedad del cliente en meses (hay clientes nuevos y clientes de siempre)
antiguedad_meses = np.clip(rng.gamma(shape=2.2, scale=14.0, size=FILAS), 1, 180).round(0)

# Plazo de crédito pactado: las cadenas negocian plazos largos, la tienda de barrio no
dias_credito = np.where(
    canal == "Cadena", rng.choice([60, 90, 120], size=FILAS, p=[0.3, 0.5, 0.2]),
    np.where(canal == "Institucional", rng.choice([45, 60, 90], size=FILAS, p=[0.3, 0.4, 0.3]),
             np.where(canal == "Mayorista", rng.choice([30, 45, 60], size=FILAS, p=[0.4, 0.4, 0.2]),
                      rng.choice([8, 15, 30], size=FILAS, p=[0.35, 0.45, 0.20])))
).astype(int)

# Monto de la factura: la cadena compra grande, la tienda de barrio compra pequeño
base_monto = np.where(canal == "Cadena", 14_000_000,
              np.where(canal == "Institucional", 9_000_000,
              np.where(canal == "Mayorista", 5_500_000, 900_000))).astype(float)
monto_factura = np.round(base_monto * rng.lognormal(mean=0.0, sigma=0.55, size=FILAS), -3)

# Historia del cliente
facturas_previas = np.clip((antiguedad_meses * rng.uniform(0.4, 2.2, FILAS)), 0, 400).round(0)

# Propensión histórica al atraso: es la variable con más señal (y es la que un
# gerente de cartera ya intuye). Se le mete ruido para que no sea un delator perfecto.
propension = np.clip(rng.beta(2.0, 5.0, FILAS)
                     + np.where(canal == "Tienda de barrio", 0.10, 0.0)
                     - np.where(canal == "Cadena", 0.04, 0.0), 0.01, 0.97)
pct_pagos_tarde_previo = np.clip(
    np.round(propension * rng.uniform(0.75, 1.25, FILAS), 3), 0.0, 1.0)

dias_atraso_promedio_previo = np.round(
    np.clip(propension * 42 * rng.uniform(0.5, 1.6, FILAS), 0, 120), 1)

tiene_acuerdo_pago = (rng.uniform(0, 1, FILAS) < (0.05 + 0.45 * propension)).astype(int)
descuento_pct = np.round(rng.choice([0.0, 2.0, 4.0, 6.0, 8.0], size=FILAS,
                                    p=[0.34, 0.26, 0.20, 0.13, 0.07]), 1)
mes = rng.integers(1, 13, FILAS)

# ---------------------------------------------------------------------------
# La regla oculta que el modelo tendrá que descubrir solo.
# Nadie se la va a contar: por eso es Machine Learning y no una fórmula de Excel.
#
# Las dos INTERACCIONES son las que hacen que valga la pena un Random Forest:
# no son "una columna sube el riesgo", son "el riesgo se dispara cuando DOS cosas
# pasan al mismo tiempo". Una línea recta no puede ver eso; un bosque de árboles sí.
# ---------------------------------------------------------------------------
interaccion_1 = ((pct_pagos_tarde_previo > 0.45) & (dias_credito <= 30)).astype(float)
# ^ cliente con mal historial Y plazo corto: no le alcanza el flujo de caja

interaccion_2 = ((monto_factura > 10_000_000) & (canal == "Institucional")).astype(float)
# ^ factura grande a una entidad pública: pasa por comité y se demora

z = (-3.10
     + 3.10 * propension                                  # su historia manda
     + 0.022 * dias_atraso_promedio_previo                # cuánto se atrasa cuando se atrasa
     + 0.70 * tiene_acuerdo_pago                          # ya venía renegociando
     + 3.00 * interaccion_1                               # la trampa que solo ven los árboles
     + 1.20 * interaccion_2                               # la segunda trampa
     + 0.30 * np.log1p(monto_factura / 1_000_000.0)       # facturas grandes se demoran más
     - 0.006 * antiguedad_meses                           # el cliente viejo cuida la relación
     - 0.004 * dias_credito                              # plazo holgado = menos atraso
     + 0.050 * descuento_pct                              # el que exige descuento aprieta la caja
     + np.where(canal == "Tienda de barrio", 0.35, 0.0)
     + np.where(canal == "Institucional", 0.28, 0.0)      # los pagos públicos se demoran
     + np.where(canal == "Cadena", -0.20, 0.0)
     + np.where(zona == "Costa", 0.20, 0.0)
     + rng.normal(0, 0.35, FILAS))                        # el azar del mundo real

prob = 1.0 / (1.0 + np.exp(-z))
pago_tarde = (rng.uniform(0, 1, FILAS) < prob).astype(int)

df = pd.DataFrame({
    "factura_id": [f"F-2026{i:05d}" for i in range(1, FILAS + 1)],
    "canal": canal,
    "zona": zona,
    "antiguedad_meses": antiguedad_meses.astype(int),
    "dias_credito_pactado": dias_credito,
    "monto_factura": monto_factura.astype("int64"),
    "facturas_previas": facturas_previas.astype(int),
    "pct_pagos_tarde_previo": pct_pagos_tarde_previo,
    "dias_atraso_promedio_previo": dias_atraso_promedio_previo,
    "tiene_acuerdo_pago": tiene_acuerdo_pago,
    "descuento_pct": descuento_pct,
    "mes": mes.astype(int),
    "pago_tarde": pago_tarde,
})

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO)
df.to_csv(destino, index=False, encoding="utf-8-sig")

tarde = int(df["pago_tarde"].sum())
print()
print("=" * 78)
print("  DATOS SINTÉTICOS GENERADOS · cartera de facturas")
print("=" * 78)
print(f"  Archivo    : {destino}")
print(f"  Filas      : {len(df):,}".replace(",", "."))
print(f"  Columnas   : {df.shape[1]}")
print(f"  Se atrasó  : {tarde} facturas de {len(df)} "
      f"({tarde / len(df) * 100:.1f} % de la cartera)")
print()
print("  Primeras 5 filas:")
print(df.head().to_string(index=False))
print()
print(f"  Recuerde: son datos SINTÉTICOS con semilla fija (SEMILLA = {SEMILLA}).")
print("  El CSV se abre con doble clic en Excel. Ya puede correr 2_entrenar.py")
print("=" * 78)
print()
