# -*- coding: utf-8 -*-
"""
Plantilla 2 - AUTOENCODER sobre datos (deteccion de anomalias)
Genera el archivo movimientos_contables.csv

QUE ES ESTO
   3.000 movimientos de pago a proveedores de una clinica: insumos medicos,
   servicios, arrendamientos, papeleria, mantenimiento. Cada fila es un pago ya
   registrado, con su monto, su hora, sus aprobadores y sus soportes.

   La pregunta NO es "prediga esto". La pregunta es:
   "de estos 3.000 pagos, cuales 30 debo mirar yo primero".

   Eso es NO SUPERVISADO: nadie marco cuales estaban raros. El modelo aprende
   como se ve un pago NORMAL y despues mide que tan lejos esta cada pago de esa
   normalidad. Lo que no logra reconstruir bien, lo levanta como sospechoso.

LA TRAMPA DEL DOCENTE
   La ultima columna del CSV se llama es_anomalia. En la vida real USTED NO LA
   TIENE: si la tuviera, no necesitaria un autoencoder, haria un clasificador
   supervisado (plantilla 1). Aqui existe solo para que al final podamos
   verificar si el modelo acerto. 2_entrenar.py la saca ANTES de entrenar y la
   vuelve a mirar SOLO al final, para calificar.

AVISO IMPORTANTE
   Los datos son SINTETICOS: los inventa este script con una semilla fija.
   No son datos de la clinica oftalmologica, ni del Area Metropolitana, ni de
   la Alcaldia de Puerto Carreno, ni de ninguna entidad real.

EL PIPELINE (paso 1 de 5)
   [1] DATOS  ->  2 preparacion  ->  3 entrenamiento  ->  4 evaluacion  ->  5 resultado
   Este script es el paso 1. Produce movimientos_contables.csv y nada mas.

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
SEMILLA = 11               # fíjela y todo el salón obtiene los mismos números
FILAS_NORMALES = 2850      # movimientos sanos
FILAS_ANOMALAS = 150       # movimientos sembrados como raros (5 % de la base)
ARCHIVO = "movimientos_contables.csv"
# ---------------------------------------------------------------------------

rng = np.random.default_rng(SEMILLA)

TIPOS = ["Insumos medicos", "Servicios", "Arrendamiento", "Papeleria", "Mantenimiento"]
PESO_TIPO = [0.34, 0.26, 0.10, 0.16, 0.14]
FORMAS = ["Transferencia", "Cheque", "Tarjeta", "Efectivo"]
PESO_FORMA = [0.62, 0.20, 0.13, 0.05]

# ===========================================================================
# LOS MOVIMIENTOS NORMALES
# Un pago sano tiene un patrón aburrido: se registra en horario de oficina,
# de lunes a viernes, con dos o tres aprobadores, con sus soportes completos,
# por un monto coherente con su tipo de gasto. El autoencoder va a aprender
# ESE aburrimiento. Todo lo que no encaje en él, le va a doler reconstruirlo.
# ===========================================================================
n = FILAS_NORMALES
tipo = rng.choice(TIPOS, size=n, p=PESO_TIPO)
forma = rng.choice(FORMAS, size=n, p=PESO_FORMA)

base = np.where(tipo == "Insumos medicos", 3_200_000,
        np.where(tipo == "Servicios", 1_800_000,
        np.where(tipo == "Arrendamiento", 8_500_000,
        np.where(tipo == "Papeleria", 320_000, 1_100_000)))).astype(float)
monto = np.round(base * rng.lognormal(0.0, 0.42, n), -3)

# Horario de oficina: campana centrada a las 11 de la mañana y a las 3 de la tarde
hora = np.clip(np.round(rng.normal(rng.choice([10.5, 15.0], n), 1.8, n)), 7, 19).astype(int)
dia_semana = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.21, 0.21, 0.20, 0.20, 0.18])

# Cuantos ojos revisaron el pago: a mayor monto, mas aprobadores (política interna)
num_aprobadores = np.clip(
    np.round(1.6 + 1.4 * np.log1p(monto / 1_000_000.0) + rng.normal(0, 0.45, n)), 1, 5
).astype(int)

# Soportes: factura, orden de compra, acta de recibido... lo normal es tenerlos todos
soportes_adjuntos = np.clip(np.round(rng.normal(3.1, 0.75, n)), 1, 5).astype(int)

dias_desde_factura = np.clip(np.round(rng.gamma(3.4, 5.2, n)), 1, 90).astype(int)
veces_proveedor_mes = np.clip(np.round(rng.gamma(2.0, 1.3, n)), 1, 12).astype(int)
pct_desviacion_presupuesto = np.round(np.clip(rng.normal(1.5, 4.2, n), -18, 22), 2)

normales = pd.DataFrame({
    "tipo_proveedor": tipo,
    "forma_pago": forma,
    "monto": monto,
    "dias_desde_factura": dias_desde_factura,
    "hora_registro": hora,
    "dia_semana": dia_semana,
    "num_aprobadores": num_aprobadores,
    "soportes_adjuntos": soportes_adjuntos,
    "veces_proveedor_mes": veces_proveedor_mes,
    "pct_desviacion_presupuesto": pct_desviacion_presupuesto,
    "es_anomalia": 0,
})

# ===========================================================================
# LOS MOVIMIENTOS ANÓMALOS
# Cuatro patrones que cualquier auditor reconoce. Ninguno es "monto alto":
# la gracia del autoencoder es que atrapa COMBINACIONES raras, no valores
# extremos sueltos. Un arrendamiento de 9 millones es normal; un pago de
# papelería de 9 millones a la 1 de la mañana con un aprobador, no.
# ===========================================================================
filas_anom = []
patrones = ["Pago fuera de horario", "Fraccionamiento / pago repetido",
            "Monto redondo sin soportes", "Sobrecosto con un solo aprobador"]

for i in range(FILAS_ANOMALAS):
    patron = patrones[i % len(patrones)]
    t = rng.choice(TIPOS, p=PESO_TIPO)
    b = {"Insumos medicos": 3_200_000, "Servicios": 1_800_000, "Arrendamiento": 8_500_000,
         "Papeleria": 320_000, "Mantenimiento": 1_100_000}[t]

    # valores de partida: se arranca de un pago normal y se le rompe UNA cosa
    fila = {
        "tipo_proveedor": t,
        "forma_pago": rng.choice(FORMAS, p=PESO_FORMA),
        "monto": float(np.round(b * rng.lognormal(0.0, 0.42), -3)),
        "dias_desde_factura": int(np.clip(round(rng.gamma(3.4, 5.2)), 1, 90)),
        "hora_registro": int(np.clip(round(rng.normal(12.0, 2.0)), 7, 19)),
        "dia_semana": int(rng.choice([1, 2, 3, 4, 5])),
        "num_aprobadores": 3,
        "soportes_adjuntos": 3,
        "veces_proveedor_mes": int(np.clip(round(rng.gamma(2.0, 1.3)), 1, 12)),
        "pct_desviacion_presupuesto": float(np.round(rng.normal(1.5, 4.2), 2)),
        "es_anomalia": 1,
    }

    if patron == "Pago fuera de horario":
        # registrado de madrugada o en fin de semana, y con menos ojos encima
        fila["hora_registro"] = int(rng.choice([0, 1, 2, 3, 4, 5, 22, 23]))
        fila["dia_semana"] = int(rng.choice([6, 7]))
        fila["num_aprobadores"] = int(rng.choice([1, 2]))

    elif patron == "Fraccionamiento / pago repetido":
        # el mismo proveedor cobrando muchas veces en el mes, montos pequeños,
        # y facturado el mismo día: el clásico partir un contrato en pedacitos
        fila["veces_proveedor_mes"] = int(rng.integers(18, 34))
        fila["monto"] = float(np.round(b * rng.uniform(0.10, 0.28), -3))
        fila["dias_desde_factura"] = int(rng.integers(1, 3))
        fila["num_aprobadores"] = 1

    elif patron == "Monto redondo sin soportes":
        # cifra exacta y sospechosamente limpia, sin papeles, y en efectivo
        fila["monto"] = float(rng.choice([5_000_000, 10_000_000, 15_000_000, 20_000_000]))
        fila["soportes_adjuntos"] = int(rng.choice([1, 1, 2]))
        fila["forma_pago"] = "Efectivo"
        fila["num_aprobadores"] = int(rng.choice([1, 2]))

    else:  # "Sobrecosto con un solo aprobador"
        # muy por encima del presupuesto, aprobado por una sola persona,
        # y con la factura vieja (se dejó vencer para meter presión)
        fila["pct_desviacion_presupuesto"] = float(np.round(rng.uniform(45, 130), 2))
        fila["num_aprobadores"] = 1
        fila["monto"] = float(np.round(b * rng.uniform(2.4, 4.5), -3))
        fila["dias_desde_factura"] = int(rng.integers(70, 120))

    fila["patron_sembrado"] = patron
    filas_anom.append(fila)

anomalos = pd.DataFrame(filas_anom)
normales["patron_sembrado"] = "-"

# ===========================================================================
# SE MEZCLAN Y SE GUARDAN
# ===========================================================================
df = pd.concat([normales, anomalos], ignore_index=True)
df = df.sample(frac=1.0, random_state=SEMILLA).reset_index(drop=True)
df.insert(0, "movimiento_id", [f"MV-2026{i:05d}" for i in range(1, len(df) + 1)])
df["monto"] = df["monto"].astype("int64")

# el orden de las columnas: primero las que el modelo mira, al final las dos
# que son solo para verificar (es_anomalia y patron_sembrado)
cols = [c for c in df.columns if c not in ("es_anomalia", "patron_sembrado")]
df = df[cols + ["es_anomalia", "patron_sembrado"]]

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO)
df.to_csv(destino, index=False, encoding="utf-8-sig")

n_anom = int(df["es_anomalia"].sum())
print()
print("=" * 78)
print("  DATOS SINTÉTICOS GENERADOS · movimientos de pago a proveedores")
print("=" * 78)
print(f"  Archivo    : {destino}")
print(f"  Filas      : {len(df):,}".replace(",", "."))
print(f"  Columnas   : {df.shape[1]}  (10 que el modelo mira + id + 2 de verificación)")
print(f"  Sembrados  : {n_anom} movimientos raros de {len(df)} "
      f"({n_anom / len(df) * 100:.1f} % de la base)")
print()
print("  Los cuatro patrones sembrados, y cuántos de cada uno:")
for p, c in df.loc[df["es_anomalia"] == 1, "patron_sembrado"].value_counts().items():
    print(f"     {c:>4}  {p}")
print()
print("  Primeras 5 filas:")
with pd.option_context("display.width", 200, "display.max_columns", 50):
    print(df.head().to_string(index=False))
print()
print(f"  Recuerde: datos SINTÉTICOS con semilla fija (SEMILLA = {SEMILLA}).")
print("  Las columnas es_anomalia y patron_sembrado son LA TRAMPA: en la vida real")
print("  usted no las tiene. 2_entrenar.py las saca antes de entrenar.")
print("  El CSV se abre con doble clic en Excel. Ya puede correr 2_entrenar.py")
print("=" * 78)
print()
