# -*- coding: utf-8 -*-
"""
Plantilla 2 - Machine Learning NO SUPERVISADO
Genera el archivo surtido_productos.csv

QUE ES ESTO
   El surtido de un supermercado: 600 referencias (SKU) con su comportamiento
   comercial del ultimo ano. NADIE etiqueto nada. No hay columna de respuesta.
   La pregunta es al reves que en la plantilla 1: en vez de "prediga esto",
   es "digame que familias hay aqui que yo no habia visto".

   Eso es NO SUPERVISADO: no hay examen, no hay Accuracy. Hay agrupamiento.

AVISO IMPORTANTE
   Los datos son SINTETICOS: los inventa este script con una semilla fija.
   No son datos de Supermo ni de Distintores ni de Vita Market. El script
   siembra cuatro familias a proposito y les mete ruido encima; el trabajo de
   K-Means sera volver a encontrarlas sin que nadie le diga cuantas hay.

   La columna familia_real que queda al final del CSV es LA TRAMPA DEL DOCENTE:
   en la vida real usted NO la tiene. Sirve solo para verificar al final si el
   modelo acerto. El script de entrenamiento la saca antes de modelar.

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
# PANEL DE CONTROL
# ---------------------------------------------------------------------------
SEMILLA = 7
ARCHIVO = "surtido_productos.csv"
# ---------------------------------------------------------------------------

rng = np.random.default_rng(SEMILLA)

# Las cuatro familias que se siembran a propósito, con su tamaño.
# Cada una es un perfil comercial que cualquier comprador reconoce.
FAMILIAS = [
    # nombre                  n    unid/mes  rotacion  margen%  %promo  devol%  quiebres
    ("Locomotora",           130,  (2400, 600), (6, 2),   (9, 2.5),  (12, 4),  (0.8, 0.4), (2.4, 1.2)),
    ("Joya de margen",       120,  (180, 70),   (46, 12), (38, 6),   (7, 3),   (1.2, 0.6), (0.5, 0.5)),
    ("Adicto a la promocion", 160, (900, 320), (17, 6),  (14, 4),   (58, 12), (4.6, 1.6), (1.6, 0.9)),
    # (el nombre va sin tilde a propósito: es un valor de CSV, y así no depende
    #  de la codificación con la que Excel abra el archivo)
    ("Cola larga dormida",   190,  (48, 26),    (96, 30), (22, 8),   (5, 3),   (2.0, 1.1), (0.3, 0.4)),
]

CATEGORIAS = ["Aseo hogar", "Bebidas", "Cuidado personal", "Despensa",
              "Lacteos", "Snacks", "Mascotas", "Panaderia"]

filas = []
n_sku = 0
for nombre, n, unid, rot, marg, promo, devol, quiebre in FAMILIAS:
    for _ in range(n):
        n_sku += 1
        filas.append({
            "sku": f"SKU-{n_sku:04d}",
            "categoria": rng.choice(CATEGORIAS),
            "unidades_mes": max(3, int(rng.normal(*unid))),
            "rotacion_dias": round(max(1.0, rng.normal(*rot)), 1),
            "margen_pct": round(max(0.5, rng.normal(*marg)), 1),
            "pct_venta_en_promocion": round(min(97.0, max(0.0, rng.normal(*promo))), 1),
            "devoluciones_pct": round(max(0.0, rng.normal(*devol)), 2),
            "quiebres_stock_mes": round(max(0.0, rng.normal(*quiebre)), 1),
            "familia_real": nombre,
        })

df = pd.DataFrame(filas)

# Precio unitario: correlacionado con el margen pero con vida propia
df["precio_unitario"] = np.round(
    (1200 + df["margen_pct"] * 380) * rng.lognormal(0, 0.42, len(df)), -1).astype("int64")

# Proveedores activos por referencia
df["proveedores_activos"] = rng.integers(1, 5, len(df))

# Se revuelven las filas: si quedaran ordenadas por familia, el ejercicio
# se resolveria mirando el CSV en vez de modelando.
df = df.sample(frac=1.0, random_state=SEMILLA).reset_index(drop=True)

# Orden de columnas: familia_real al final, para que se vea que es un apendice
orden = ["sku", "categoria", "precio_unitario", "unidades_mes", "rotacion_dias",
         "margen_pct", "pct_venta_en_promocion", "devoluciones_pct",
         "quiebres_stock_mes", "proveedores_activos", "familia_real"]
df = df[orden]

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO)
df.to_csv(destino, index=False, encoding="utf-8-sig")

print()
print("=" * 78)
print("  DATOS SINTÉTICOS GENERADOS · surtido de un supermercado")
print("=" * 78)
print(f"  Archivo    : {destino}")
print(f"  Referencias: {len(df)} SKU")
print(f"  Columnas   : {df.shape[1]}  (7 numéricas de comportamiento comercial)")
print()
print("  Familias sembradas a propósito (el modelo NO las va a ver):")
for nombre, cuenta in df["familia_real"].value_counts().items():
    print(f"     {nombre:<24} {cuenta:>4} referencias")
print()
print("  Primeras 5 filas:")
print(df.head().to_string(index=False))
print()
print(f"  Datos SINTÉTICOS con semilla fija (SEMILLA = {SEMILLA}).")
print("  Ya puede correr 2_entrenar.py")
print("=" * 78)
print()
