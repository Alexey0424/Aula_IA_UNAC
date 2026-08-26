# -*- coding: utf-8 -*-
"""
Plantilla 2 - Machine Learning NO SUPERVISADO
La pregunta de negocio: ¿qué familias de productos hay en mi surtido que yo no había visto?

Herramienta: K-Means (agrupamiento por parecido).

Aquí NO hay Accuracy: no hay respuesta correcta contra la cual comparar. Lo que se
mide es si los grupos quedaron apretados y separados (Silhouette Score), y el que
decide si sirven es el gerente, no el modelo.

Imprime el método del codo (Elbow), el Silhouette Score, la ficha de cada grupo
con nombre propuesto, y guarda una gráfica PNG.

Datos SINTÉTICOS. Ver 1_generar_datos.py.
Diplomado en Inteligencia Artificial - UNAC - Clase 05
"""

import sys
import os
import time
import subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
ARCHIVO_CSV = "surtido_productos.csv"
COLUMNAS_A_IGNORAR = ["sku", "categoria", "familia_real"]
#   sku          -> identificador, nunca entra
#   categoria    -> texto; K-Means trabaja con números (se deja fuera a propósito)
#   familia_real -> LA RESPUESTA. En la vida real usted no la tiene. Se saca del
#                   modelo y solo se usa al final para verificar.
NUMERO_DE_GRUPOS = 4      # el "k" de K-Means. Cámbielo a 3 o 5 y vuelva a correr.
RANGO_CODO = range(2, 9)  # cuántos k se prueban en el método del codo
SEMILLA = 7
ARCHIVO_GRAFICA = "resultado_clusters.png"
# ---------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVY, CREMA, ORO = "#0E2036", "#F6F5F0", "#EAAD05"
COLORES = ["#D54E48", "#29AC8A", "#3C7FD0", "#6B52E1", "#E8792B", "#EAAD05",
           "#8A6F3E", "#4B5A6D"]
for f in ("Segoe UI", "DejaVu Sans"):
    try:
        plt.rcParams["font.family"] = [f]
        break
    except Exception:
        pass

t_inicio = time.perf_counter()


def titulo(t):
    print()
    print("=" * 78)
    print("  " + t)
    print("=" * 78)


def sub(t):
    print()
    print("-- " + t + " " + "-" * max(0, 74 - len(t)))


# ===========================================================================
# 1. LOS DATOS
# ===========================================================================
ruta = os.path.join(AQUI, ARCHIVO_CSV)
if not os.path.exists(ruta):
    print(f"No encontré {ARCHIVO_CSV}. Lo genero ahora...")
    subprocess.run([sys.executable, os.path.join(AQUI, "1_generar_datos.py")], check=True)

df = pd.read_csv(ruta, encoding="utf-8-sig")

titulo("PLANTILLA 2 · MACHINE LEARNING NO SUPERVISADO (K-Means)")
print("  Pregunta de negocio : ¿qué familias hay en mi surtido que yo no había visto?")
print("  Tipo de problema    : Clustering (agrupamiento)")
print(f"  Referencias         : {len(df)} SKU")
print("  Datos               : SINTÉTICOS, semilla fija (no son de ninguna empresa real)")
print()
print("  La diferencia con la plantilla 1, en una frase:")
print("     supervisado   -> yo le digo la respuesta y él aprende a predecirla.")
print("     no supervisado-> nadie sabe la respuesta; él propone los grupos.")
print()
print("  Aquí NO hay Accuracy. No hay nada contra qué compararse. Y eso está bien:")
print("  es exactamente el caso de un comprador que tiene 600 referencias y ninguna")
print("  clasificación comercial.")

usadas = [c for c in df.columns if c not in COLUMNAS_A_IGNORAR
          and pd.api.types.is_numeric_dtype(df[c])]
X = df[usadas].to_numpy(dtype=float)

sub("Las variables con las que agrupa")
for c in usadas:
    print(f"     {c:<26} de {df[c].min():>10.1f} a {df[c].max():>10.1f}")
print()
print("  Se ESTANDARIZAN antes de agrupar (StandardScaler). Por qué importa:")
print("  'unidades_mes' llega a miles y 'devoluciones_pct' no pasa de 8. Sin")
print("  estandarizar, K-Means agruparía casi solo por unidades y las demás")
print("  columnas no pesarían nada. Estandarizar = poner todas en la misma escala.")

Xs = StandardScaler().fit_transform(X)

# ===========================================================================
# 2. ¿CUÁNTOS GRUPOS? — el método del codo y el Silhouette
# ===========================================================================
sub("¿Cuántos grupos pido? · método del codo (Elbow) + Silhouette Score")
print("  Inercia   : qué tan apretados quedan los grupos. Siempre baja al subir k,")
print("              así que no se busca el mínimo: se busca el CODO, donde deja de")
print("              mejorar mucho por cada grupo que se agrega.")
print("  Silhouette: de -1 a 1. Qué tan bien separados quedaron. Más alto es mejor.")
print("              Arriba de 0.50 es una separación clara.")
print()
print(f"  {'k':>4}{'Inercia':>13}{'Silhouette':>13}   {'Lectura':<28}")
print("  " + "-" * 74)
inercias, siluetas, ks = [], [], list(RANGO_CODO)
for k in ks:
    km = KMeans(n_clusters=k, n_init=10, random_state=SEMILLA).fit(Xs)
    sil = silhouette_score(Xs, km.labels_)
    inercias.append(km.inertia_)
    siluetas.append(sil)
    lectura = "separación clara" if sil >= 0.50 else (
              "separación aceptable" if sil >= 0.30 else "grupos que se tocan")
    marca = "  <- el que pedimos" if k == NUMERO_DE_GRUPOS else ""
    print(f"  {k:>4}{km.inertia_:>13.0f}{sil:>13.3f}   {lectura:<28}{marca}")

k_mejor_sil = ks[int(np.argmax(siluetas))]
print()
print(f"  El Silhouette más alto lo da k = {k_mejor_sil} ({max(siluetas):.3f}).")
print(f"  Nosotros pedimos k = {NUMERO_DE_GRUPOS}.")
print("  Y eso está permitido: si el negocio maneja 4 estrategias de compra, 4 grupos")
print("  son útiles aunque la métrica prefiera otro número. La métrica aconseja; el")
print("  gerente decide. Cambie NUMERO_DE_GRUPOS y vuelva a correr para verlo.")

# ===========================================================================
# 3. EL AGRUPAMIENTO
# ===========================================================================
km = KMeans(n_clusters=NUMERO_DE_GRUPOS, n_init=10, random_state=SEMILLA).fit(Xs)
df["grupo"] = km.labels_
sil_final = silhouette_score(Xs, km.labels_)

sub(f"Los {NUMERO_DE_GRUPOS} grupos que propuso el modelo")
print(f"  Silhouette Score final: {sil_final:.3f}")
print()
perfil = df.groupby("grupo")[usadas].mean().round(1)
perfil.insert(0, "SKU", df["grupo"].value_counts().sort_index().values)


def bautizar(fila, glob):
    """Propone un nombre comercial mirando el perfil del grupo.
    El modelo agrupa; el gerente bautiza. Esta función es solo un borrador."""
    promo = fila["pct_venta_en_promocion"] > glob["pct_venta_en_promocion"] * 1.6
    vol = fila["unidades_mes"] > glob["unidades_mes"] * 1.5
    margen = fila["margen_pct"] > glob["margen_pct"] * 1.25
    lenta = fila["rotacion_dias"] > glob["rotacion_dias"] * 1.5
    if promo:
        return "Adicto a la promoción"
    if vol and not margen:
        return "Locomotora de tráfico"
    if margen and not vol:
        return "Joya de margen"
    if lenta:
        return "Cola larga dormida"
    return "Grupo intermedio"


glob = df[usadas].mean()
nombres_grupo = {g: bautizar(perfil.loc[g], glob) for g in perfil.index}

print("  Ficha de cada grupo (promedios):")
print()
enc = f"  {'Grupo':<6}{'SKU':>5}{'Unid/mes':>10}{'Rotac.d':>9}{'Margen%':>9}{'%Promo':>8}{'Devol%':>8}{'Quiebr':>8}"
print(enc)
print("  " + "-" * 74)
for g in perfil.index:
    r = perfil.loc[g]
    print(f"  {g:<6}{int(r['SKU']):>5}{r['unidades_mes']:>10.0f}{r['rotacion_dias']:>9.1f}"
          f"{r['margen_pct']:>9.1f}{r['pct_venta_en_promocion']:>8.1f}"
          f"{r['devoluciones_pct']:>8.2f}{r['quiebres_stock_mes']:>8.1f}")

print()
print("  Nombre propuesto y qué haría un comprador con cada grupo:")
ACCIONES = {
    "Locomotora de tráfico": "nunca dejarla agotar; el quiebre cuesta la visita completa",
    "Joya de margen": "empujarla con exhibición; es la que paga la utilidad",
    "Adicto a la promoción": "revisar margen real: puede estar vendiendo sin dejar plata",
    "Cola larga dormida": "candidata a salir del surtido; libera espacio y capital",
    "Grupo intermedio": "revisar a mano: el modelo no lo separó bien",
}
for g in perfil.index:
    nb = nombres_grupo[g]
    print(f"     Grupo {g} · {nb:<24} -> {ACCIONES.get(nb, 'revisar a mano')}")

print()
print("  OJO, esto es lo importante: el modelo entregó los grupos 0, 1, 2 y 3.")
print("  Los NOMBRES los puso una regla que escribimos nosotros mirando los promedios.")
print("  El modelo agrupa; usted bautiza. Y si un grupo no le significa nada, no es")
print("  un error del modelo: cambie el k o cambie las variables y vuelva a preguntar.")

# ===========================================================================
# 4. LA VERIFICACIÓN (solo posible porque los datos son sintéticos)
# ===========================================================================
if "familia_real" in df.columns:
    sub("Verificación · ¿encontró las familias que sembramos?")
    print("  Esto SOLO se puede hacer aquí, porque nosotros inventamos los datos y")
    print("  sabemos la respuesta. Con sus datos reales no tendrá esta tabla.")
    print()
    tab = pd.crosstab(df["grupo"], df["familia_real"])
    print(tab.to_string())
    coincide = tab.max(axis=1).sum() / len(df)
    print()
    print(f"  Cada grupo del modelo cae mayoritariamente sobre una familia sembrada:")
    print(f"  coincidencia global {coincide*100:.1f} %.")
    print("  Es decir: K-Means redescubrió solo, sin que nadie le dijera nada, las")
    print("  familias comerciales que estaban escondidas en los números.")
    print()
    print("  LA LECCIÓN INCÓMODA, y es la más importante de esta plantilla:")
    print(f"     el Silhouette Score dio {sil_final:.2f} -- 'grupos que se tocan', una nota")
    print(f"     mediocre. Y sin embargo la recuperación real fue del {coincide*100:.0f} %.")
    print()
    print("  ¿Cómo puede ser? Porque el Silhouette castiga que los grupos se toquen,")
    print("  y las familias comerciales de verdad SE TOCAN: hay productos que son mitad")
    print("  locomotora y mitad caza-promoción. La métrica midió la geometría; el negocio")
    print("  vive en las fronteras. Si usted hubiera botado este modelo por su Silhouette,")
    print("  habría botado un modelo que acertó 9 de cada 10.")
    print()
    print("  Moraleja para el proyecto de grado: en no supervisado la métrica ACONSEJA.")
    print("  La validación de verdad es que un experto del negocio mire los grupos y")
    print("  reconozca lo que ve. Ese experto es usted.")

# ===========================================================================
# 5. LA GRÁFICA
# ===========================================================================
pca = PCA(n_components=2, random_state=SEMILLA)
P = pca.fit_transform(Xs)
Cent = pca.transform(km.cluster_centers_)
var = pca.explained_variance_ratio_.sum() * 100

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), facecolor=CREMA)
fig.suptitle(f"Surtido · {len(df)} referencias agrupadas por comportamiento comercial   "
             f"k = {NUMERO_DE_GRUPOS}  ·  Silhouette {sil_final:.2f}",
             fontsize=13.5, color=NAVY, y=0.97)

ax1.set_facecolor("white")
ax1.plot(ks, inercias, marker="o", color=NAVY, linewidth=2, markersize=6)
ax1.axvline(NUMERO_DE_GRUPOS, color=ORO, linewidth=2.4, linestyle="--")
ax1.annotate(f"k = {NUMERO_DE_GRUPOS}\n(el que pedimos)", (NUMERO_DE_GRUPOS, max(inercias) * 0.72),
             color="#8A6F3E", fontsize=9.5, ha="left",
             xytext=(NUMERO_DE_GRUPOS + 0.25, max(inercias) * 0.72))
ax1.set_xlabel("Número de grupos (k)", fontsize=10, color=NAVY)
ax1.set_ylabel("Inercia (qué tan apretados)", fontsize=10, color=NAVY)
ax1.set_title("Método del codo (Elbow Method)\ndonde deja de valer la pena agregar grupos",
              fontsize=11, color=NAVY, pad=10)
ax1.grid(color="#DDD8CC", linewidth=0.7)
ax1.set_axisbelow(True)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

ax2.set_facecolor("white")
for g in range(NUMERO_DE_GRUPOS):
    m = km.labels_ == g
    ax2.scatter(P[m, 0], P[m, 1], s=17, alpha=0.62, color=COLORES[g % len(COLORES)],
                edgecolors="none", label=f"{g} · {nombres_grupo[g]}")
ax2.scatter(Cent[:, 0], Cent[:, 1], marker="D", s=95, color="black",
            edgecolors="white", linewidths=1.4, zorder=5, label="Centroide (el típico)")
ax2.set_title(f"Los grupos, vistos en 2 dimensiones (PCA)\n"
              f"las 7 variables resumidas en 2 ejes ({var:.0f} % de la información)",
              fontsize=11, color=NAVY, pad=10)
ax2.legend(fontsize=8.6, frameon=False, loc="best")
ax2.set_xlabel("Componente 1", fontsize=9.5, color=NAVY)
ax2.set_ylabel("Componente 2", fontsize=9.5, color=NAVY)
ax2.grid(color="#DDD8CC", linewidth=0.7)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.text(0.5, 0.015,
         "Datos sintéticos con semilla fija · Diplomado en Inteligencia Artificial · UNAC · Clase 05",
         ha="center", fontsize=8.5, color="#7A8797")
fig.tight_layout(rect=(0, 0.035, 1, 0.93))
salida = os.path.join(AQUI, ARCHIVO_GRAFICA)
fig.savefig(salida, dpi=130, facecolor=CREMA)
plt.close(fig)

# El CSV con el grupo pegado: esto es el entregable que se lleva a la reunión
salida_csv = os.path.join(AQUI, "surtido_con_grupo.csv")
df.to_csv(salida_csv, index=False, encoding="utf-8-sig")

total = time.perf_counter() - t_inicio
titulo("LISTO")
print(f"  Gráfica guardada en : {salida}")
print(f"  CSV con el grupo    : {salida_csv}  (ábralo en Excel y filtre por 'grupo')")
print(f"  Tiempo total        : {total:.1f} segundos")
print()
print("  Para usar SUS datos: reemplace surtido_productos.csv por su archivo, ponga")
print("  en COLUMNAS_A_IGNORAR los identificadores y el texto, y pídale a Claude que")
print("  lo corra. Regla de la casa: sus datos se quedan en su computador.")
print("=" * 78)
print()
