# -*- coding: utf-8 -*-
"""
Plantilla 3 - DEEP LEARNING con red convolucional (CNN)
Genera el archivo imagenes_vidrio.npz + una hoja de contactos en PNG

QUE ES ESTO
   2.400 fotos (simuladas) de laminas de vidrio saliendo de la linea de corte,
   en escala de grises de 28x28 pixeles. Cuatro clases:

      0  OK          la lamina esta bien
      1  Rayon       una raya fina cruzando la lamina  (scratch)
      2  Burbuja     una burbuja de aire en el interior (bubble)
      3  Astillado   el borde salio picado              (chipped edge)

   La pregunta de negocio: clasificar imagenes. Que el computador mire la foto
   y diga si la pieza pasa o en que fallo, sin que un operario revise una por una.

POR QUE UNA CNN Y NO UN RANDOM FOREST
   Un modelo clasico mira cada pixel como una columna suelta e independiente.
   Un rayon movido tres pixeles a la derecha es, para el, una fila de datos
   completamente distinta. La CONVOLUCION mira VECINDARIOS de pixeles: aprende
   "raya diagonal" como concepto y la reconoce en cualquier parte de la imagen.
   Por eso las imagenes son el territorio del Deep Learning y no del Excel.

   El script de entrenamiento demuestra esto: corre los dos y compara.

AVISO IMPORTANTE
   Las imagenes son SINTETICAS: las dibuja este script con numpy y una semilla
   fija. No son fotos de Coti Vidrios ni de ninguna planta real. Se hacen asi
   para que la plantilla corra sin descargar ni un byte y sin depender de
   internet en clase.

Diplomado en Inteligencia Artificial - UNAC - Clase 05
"""

import sys
import os
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np

# ---------------------------------------------------------------------------
# PANEL DE CONTROL
# ---------------------------------------------------------------------------
SEMILLA = 2026
IMAGENES_POR_CLASE = 600     # 4 clases x 600 = 2.400 imágenes
LADO = 28                    # 28 x 28 píxeles, como el MNIST clásico
ARCHIVO = "imagenes_vidrio.npz"
HOJA_CONTACTOS = "muestras_vidrio.png"
# ---------------------------------------------------------------------------

CLASES = ["OK", "Rayon", "Burbuja", "Astillado"]
rng = np.random.default_rng(SEMILLA)
t0 = time.perf_counter()


def lamina_base():
    """El vidrio limpio: un degradado suave (la luz de la nave) + grano del sensor."""
    yy, xx = np.mgrid[0:LADO, 0:LADO] / (LADO - 1.0)
    ang = rng.uniform(0, 2 * np.pi)
    degradado = 0.5 + 0.16 * (np.cos(ang) * (xx - 0.5) + np.sin(ang) * (yy - 0.5)) * 2
    brillo = rng.uniform(0.86, 1.14)
    img = degradado * brillo + rng.normal(0, 0.045, (LADO, LADO))
    return img


def poner_rayon(img):
    """Una raya fina y recta, en ángulo cualquiera, más clara o más oscura."""
    yy, xx = np.mgrid[0:LADO, 0:LADO].astype(float)
    ang = rng.uniform(0, np.pi)
    cx, cy = rng.uniform(7, LADO - 7), rng.uniform(7, LADO - 7)
    # distancia de cada píxel a la recta que pasa por (cx,cy) con ángulo ang
    d = np.abs(np.sin(ang) * (xx - cx) - np.cos(ang) * (yy - cy))
    grosor = rng.uniform(0.55, 1.05)
    fuerza = rng.uniform(0.30, 0.52) * rng.choice([-1.0, 1.0])
    img += fuerza * np.exp(-(d / grosor) ** 2)
    return img


def poner_burbuja(img):
    """Una burbuja: un puntico redondo y brillante con halo oscuro alrededor."""
    yy, xx = np.mgrid[0:LADO, 0:LADO].astype(float)
    cx, cy = rng.uniform(6, LADO - 6), rng.uniform(6, LADO - 6)
    r = rng.uniform(1.5, 2.9)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    img += rng.uniform(0.34, 0.55) * np.exp(-(d / r) ** 2)          # el brillo
    img -= rng.uniform(0.14, 0.24) * np.exp(-((d - r * 1.9) / (r * 0.85)) ** 2)  # el halo
    return img


def poner_astillado(img):
    """El borde picado: una mordida en uno de los cuatro bordes de la lámina."""
    lado = rng.integers(0, 4)
    largo = rng.integers(8, 16)
    prof = rng.integers(3, 7)
    ini = rng.integers(0, LADO - largo)
    mordida = rng.uniform(0.03, 0.16)      # el vidrio roto se ve oscuro
    dientes = rng.uniform(0.5, 1.0, largo)
    for i in range(largo):
        p = max(1, int(round(prof * dientes[i])))
        if lado == 0:
            img[0:p, ini + i] = mordida + rng.normal(0, 0.03, p)
        elif lado == 1:
            img[LADO - p:LADO, ini + i] = mordida + rng.normal(0, 0.03, p)
        elif lado == 2:
            img[ini + i, 0:p] = mordida + rng.normal(0, 0.03, p)
        else:
            img[ini + i, LADO - p:LADO] = mordida + rng.normal(0, 0.03, p)
    return img


DEFECTOS = {1: poner_rayon, 2: poner_burbuja, 3: poner_astillado}

X = np.zeros((IMAGENES_POR_CLASE * 4, LADO, LADO), dtype=np.float32)
y = np.zeros(IMAGENES_POR_CLASE * 4, dtype=np.int64)

i = 0
for clase in range(4):
    for _ in range(IMAGENES_POR_CLASE):
        img = lamina_base()
        if clase in DEFECTOS:
            img = DEFECTOS[clase](img)
        # Desenfoque suave (3x3): la cámara de planta no es un microscopio.
        # Es lo que evita que el problema quede demasiado fácil.
        pad = np.pad(img, 1, mode="edge")
        suave = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]
                 + 4.0 * pad[1:-1, 1:-1]) / 8.0
        X[i] = np.clip(suave, 0.0, 1.0).astype(np.float32)
        y[i] = clase
        i += 1

# Se revuelven las filas antes de guardar
orden = rng.permutation(len(y))
X, y = X[orden], y[orden]

AQUI = os.path.dirname(os.path.abspath(__file__))
destino = os.path.join(AQUI, ARCHIVO)
np.savez_compressed(destino, X=X, y=y, clases=np.array(CLASES))

# ---------------------------------------------------------------------------
# Hoja de contactos: para que el gerente VEA con qué está trabajando.
# Regla de la casa: nunca entrene con datos que no ha mirado.
# ---------------------------------------------------------------------------
hoja = None
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for f in ("Segoe UI", "DejaVu Sans"):
        try:
            plt.rcParams["font.family"] = [f]
            break
        except Exception:
            pass
    fig, axes = plt.subplots(4, 8, figsize=(11.2, 6.0), facecolor="#F6F5F0")
    fig.suptitle("Las cuatro clases que la red tendrá que aprender a distinguir\n"
                 "imágenes SINTÉTICAS de 28 x 28 píxeles, generadas con semilla fija",
                 fontsize=12.5, color="#0E2036", y=0.98)
    for fila, clase in enumerate(range(4)):
        idx = np.where(y == clase)[0][:8]
        for col, j in enumerate(idx):
            ax = axes[fila, col]
            ax.imshow(X[j], cmap="gray", vmin=0, vmax=1)
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color("#DDD8CC")
            if col == 0:
                ax.set_ylabel(f"{clase} · {CLASES[clase]}", fontsize=10.5,
                              color="#0E2036", rotation=0, ha="right", va="center",
                              labelpad=14)
    fig.text(0.5, 0.02, "Datos sintéticos · Diplomado en Inteligencia Artificial · UNAC · Clase 05",
             ha="center", fontsize=8.5, color="#7A8797")
    fig.tight_layout(rect=(0.04, 0.04, 1, 0.92))
    hoja = os.path.join(AQUI, HOJA_CONTACTOS)
    fig.savefig(hoja, dpi=130, facecolor="#F6F5F0")
    plt.close(fig)
except Exception as e:
    print(f"  (No se pudo dibujar la hoja de contactos: {e})")

mb = os.path.getsize(destino) / 1024 / 1024
print()
print("=" * 78)
print("  IMÁGENES SINTÉTICAS GENERADAS · control de calidad de láminas de vidrio")
print("=" * 78)
print(f"  Archivo    : {destino}")
print(f"  Peso       : {mb:.2f} MB")
print(f"  Imágenes   : {len(y)}  de {LADO} x {LADO} píxeles en escala de grises")
print(f"  Clases     : {', '.join(f'{i}={c}' for i, c in enumerate(CLASES))}")
print(f"  Por clase  : {IMAGENES_POR_CLASE} cada una (perfectamente balanceadas)")
if hoja:
    print(f"  Muestras   : {hoja}  <- ÁBRALA. Mire los defectos antes de entrenar.")
print(f"  Generadas en {time.perf_counter()-t0:.1f} segundos, sin descargar nada.")
print()
print(f"  Datos SINTÉTICOS con semilla fija (SEMILLA = {SEMILLA}).")
print("  Ya puede correr 2_entrenar.py")
print("=" * 78)
print()
