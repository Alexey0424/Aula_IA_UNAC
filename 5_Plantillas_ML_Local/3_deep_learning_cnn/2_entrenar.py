# -*- coding: utf-8 -*-
"""
Plantilla 3 - DEEP LEARNING con red convolucional (CNN)
La pregunta de negocio: clasificar imágenes. ¿Esta lámina de vidrio pasa, o en qué falló?

Esta plantilla corre DOS modelos y los compara:

   A) Logistic Regression sobre los 784 píxeles sueltos  (el modelo clásico)
      Mira cada píxel como una columna independiente. No sabe que el píxel de
      al lado existe.

   B) Convolutional Neural Network - CNN               (el Deep Learning)
      Mira VECINDARIOS de píxeles. Aprende "raya diagonal" y la reconoce en
      cualquier parte de la lámina.

   La diferencia entre A y B es toda la lección de la clase.

ADVERTENCIA DE PESO Y TIEMPO - LÉALA ANTES DE CORRER
   Esta es la única plantilla que necesita una instalación EXTRA: PyTorch.
   Son ~127 MB de descarga y deja ~640 MB en el disco duro. Las otras dos
   plantillas no necesitan nada de esto.
   Si está en clase con internet compartido, NO la instale en vivo: esta
   plantilla es para hacerla en casa.
   La línea exacta está en 0_instalar.txt (LÍNEA 2).

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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
ARCHIVO_DATOS = "imagenes_vidrio.npz"
PORCENTAJE_EXAMEN = 0.20     # 20 % de las imágenes se guardan para el examen
EPOCAS = 15                  # cuántas veces la red repasa todas las imágenes
TAMANO_LOTE = 64             # de cuántas en cuántas mira las imágenes
TASA_APRENDIZAJE = 0.002     # qué tan grandes son los pasos que da al corregir
SEMILLA = 2026
CORRER_MODELO_CLASICO = True  # el comparativo. Póngalo en False si tiene prisa.
ARCHIVO_GRAFICA = "resultado_cnn.png"
# ---------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVY, CREMA, ORO = "#0E2036", "#F6F5F0", "#EAAD05"
AZUL, ROJO, TEAL = "#3C7FD0", "#D54E48", "#29AC8A"
for f in ("Segoe UI", "DejaVu Sans"):
    try:
        plt.rcParams["font.family"] = [f]
        break
    except Exception:
        pass


def titulo(t):
    print()
    print("=" * 78)
    print("  " + t)
    print("=" * 78)


def sub(t):
    print()
    print("-- " + t + " " + "-" * max(0, 74 - len(t)))


t_inicio = time.perf_counter()

# ===========================================================================
# 0. ¿ESTÁ PYTORCH?
# ===========================================================================
try:
    import torch
    import torch.nn as nn
except ImportError as e:
    print()
    print("=" * 78)
    print("  FALTA PYTORCH - o se equivocó de Python")
    print("=" * 78)
    print(f"  Python no encontró: {getattr(e, 'name', 'torch')}")
    print()
    print("  Esta plantilla corre en el ENTORNO 2 (el de torch), el mismo de la")
    print("  plantilla 2. Se corre escribiendo su Python completo:")
    print()
    print("      C:\\ia\\env_deep\\Scripts\\python.exe 2_entrenar.py")
    print()
    print("  NO se corre con 'py' ni con 'python' a secas.")
    print()
    print("  Si todavía no ha creado ese entorno, la receta completa está en")
    print("  0_instalar.txt (PASO 2). En resumen, y NO en clase con el internet")
    print("  compartido (es más de 1 GB):")
    print()
    print("      py -m venv C:\\ia\\env_deep")
    print("      C:\\ia\\env_deep\\Scripts\\python.exe -m pip install torch "
          "scikit-learn pandas matplotlib numpy")
    print()
    print("  En Windows esa línea trae la versión de CPU. No necesita tarjeta")
    print("  gráfica, no necesita CUDA, no necesita --index-url.")
    print()
    print("  OJO: NO instale PyCaret en este entorno ni torch en el de PyCaret.")
    print("  Se rompen entre ellos (PyCaret exige numpy 1.x; torch exige numpy 2.x),")
    print("  y torch se rompe EN SILENCIO: pip dice que quedó bien y luego falla")
    print("  con 'OSError: [WinError 1114] ... c10.dll'.")
    print()
    print("  Si le sale un error de 'long paths' o 'ruta demasiado larga':")
    print("  es el límite de 260 caracteres de Windows. Por eso el entorno va en")
    print("  C:\\ia y no dentro de esta carpeta.")
    print("=" * 78)
    print()
    sys.exit(1)

torch.manual_seed(SEMILLA)
np.random.seed(SEMILLA)

# ===========================================================================
# 1. LOS DATOS
# ===========================================================================
ruta = os.path.join(AQUI, ARCHIVO_DATOS)
if not os.path.exists(ruta):
    print(f"No encontré {ARCHIVO_DATOS}. Lo genero ahora...")
    subprocess.run([sys.executable, os.path.join(AQUI, "1_generar_datos.py")], check=True)

d = np.load(ruta, allow_pickle=False)
X, y = d["X"], d["y"]
CLASES = [str(c) for c in d["clases"]]
n_clases = len(CLASES)

titulo("PLANTILLA 3 · DEEP LEARNING · RED CONVOLUCIONAL (CNN)")
print("  Pregunta de negocio : ¿esta lámina de vidrio pasa, o en qué falló?")
print("  Tipo de problema    : clasificación de imágenes, 4 clases")
print(f"  Imágenes            : {len(y)} de 28 x 28 píxeles en escala de grises")
print(f"  Clases              : {', '.join(f'{i}={c}' for i, c in enumerate(CLASES))}")
print("  Datos               : SINTÉTICOS (no son fotos de ninguna planta real)")
print(f"  PyTorch             : {torch.__version__}   ·   CUDA disponible: "
      f"{torch.cuda.is_available()}")
print(f"  Corriendo en        : CPU con {torch.get_num_threads()} hilos "
      "(no se necesita tarjeta gráfica)")

# train/test split estratificado, hecho a mano para no depender de sklearn aquí
rng = np.random.default_rng(SEMILLA)
idx_tr, idx_te = [], []
for c in range(n_clases):
    idx = np.where(y == c)[0]
    rng.shuffle(idx)
    corte = int(round(len(idx) * PORCENTAJE_EXAMEN))
    idx_te.extend(idx[:corte])
    idx_tr.extend(idx[corte:])
idx_tr = np.array(idx_tr); idx_te = np.array(idx_te)
rng.shuffle(idx_tr); rng.shuffle(idx_te)

Xtr, ytr = X[idx_tr], y[idx_tr]
Xte, yte = X[idx_te], y[idx_te]

sub("train/test split · el mismo examen para los dos modelos")
print(f"  Estudia con : {len(ytr)} imágenes")
print(f"  Se examina  : {len(yte)} imágenes  -- estas NO las vio nunca")
print("  Las cuatro clases están balanceadas (600 imágenes cada una), así que aquí")
print("  el Accuracy sí es una medida honesta: adivinar al azar entre 4 clases da")
print("  25 %. Ese es el piso contra el que hay que comparar cualquier resultado.")

# ===========================================================================
# 2. MODELO A · EL CLÁSICO, PÍXEL POR PÍXEL
# ===========================================================================
acc_clasico, seg_clasico = None, None
if CORRER_MODELO_CLASICO:
    sub("Modelo A · Logistic Regression sobre los 784 píxeles sueltos")
    print("  Le entregamos la imagen ESTIRADA: 28 x 28 = 784 columnas, una por")
    print("  píxel. Para este modelo el píxel (0,0) y el píxel (0,1) son dos")
    print("  columnas cualesquiera, sin relación. No sabe que son vecinos.")
    try:
        from sklearn.linear_model import LogisticRegression
        t0 = time.perf_counter()
        # OJO: no se pasa multi_class=... El parámetro se eliminó en
        # scikit-learn 1.7; con sklearn nuevo esa línea revienta. Sin el
        # parámetro, sklearn hace multiclase automáticamente.
        clas = LogisticRegression(max_iter=400, n_jobs=-1)
        clas.fit(Xtr.reshape(len(Xtr), -1), ytr)
        acc_clasico = float((clas.predict(Xte.reshape(len(Xte), -1)) == yte).mean())
        seg_clasico = time.perf_counter() - t0
        print(f"  Accuracy en el examen: {acc_clasico:.3f}   "
              f"(entrenó en {seg_clasico:.1f} s)")
    except Exception as e:
        print(f"  (No se pudo correr el comparativo: {e})")
        acc_clasico = None

# ===========================================================================
# 3. MODELO B · LA CNN
# ===========================================================================
sub("Modelo B · la red convolucional (CNN)")
print("  Cómo está armada, en lenguaje de planta:")
print("     Conv 1 -> 8 filtros de 3x3    ocho 'lupas' que barren toda la lámina")
print("               ReLU + MaxPool       se queda con lo que encontró y encoge a 14x14")
print("     Conv 2 -> 16 filtros de 3x3   dieciséis lupas sobre lo que halló la primera")
print("               ReLU + MaxPool       encoge a 7x7")
print("     Aplanar -> 64 neuronas -> 4 salidas (una por clase)")
print()
print("  LA IDEA CLAVE: nadie le programó qué es un rayón. Los filtros arrancan")
print("  con números al azar y, a fuerza de ver ejemplos, se van convirtiendo en")
print("  detectores de bordes, de puntos y de manchas. Las capas del medio")
print("  INVENTAN sus propias columnas. Eso es Deep Learning.")


class CNN(nn.Module):
    def __init__(self, n_salidas):
        super().__init__()
        self.rasgos = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.decide = nn.Sequential(
            nn.Flatten(), nn.Linear(16 * 7 * 7, 64), nn.ReLU(),
            nn.Linear(64, n_salidas),
        )

    def forward(self, x):
        return self.decide(self.rasgos(x))


red = CNN(n_clases)
n_par = sum(p.numel() for p in red.parameters())
print()
print(f"  Parámetros de la red: {n_par:,}".replace(",", ".") +
      "  (un LLM tiene miles de millones; esta cabe en un correo)")

Ttr = torch.from_numpy(Xtr).unsqueeze(1)      # (N, 1, 28, 28) - el 1 es "un solo canal"
Ytr = torch.from_numpy(ytr)
Tte = torch.from_numpy(Xte).unsqueeze(1)
Yte = torch.from_numpy(yte)

perdida_fn = nn.CrossEntropyLoss()
opt = torch.optim.Adam(red.parameters(), lr=TASA_APRENDIZAJE)

print()
print(f"  Entrenando {EPOCAS} épocas (una época = repasar las {len(ytr)} imágenes):")
print()
print(f"  {'Época':>7}{'Pérdida':>11}{'Acc. estudio':>15}{'Acc. examen':>14}{'seg':>8}")
print("  " + "-" * 74)

hist = {"epoca": [], "perdida": [], "acc_tr": [], "acc_te": []}
t_entren = time.perf_counter()
for ep in range(1, EPOCAS + 1):
    t_ep = time.perf_counter()
    red.train()
    perm = torch.randperm(len(Ytr))
    total = 0.0
    for i in range(0, len(perm), TAMANO_LOTE):
        lote = perm[i:i + TAMANO_LOTE]
        opt.zero_grad()
        salida = red(Ttr[lote])
        p = perdida_fn(salida, Ytr[lote])
        p.backward()
        opt.step()
        total += float(p) * len(lote)
    red.eval()
    with torch.no_grad():
        acc_tr = float((red(Ttr).argmax(1) == Ytr).float().mean())
        acc_te = float((red(Tte).argmax(1) == Yte).float().mean())
    seg = time.perf_counter() - t_ep
    hist["epoca"].append(ep); hist["perdida"].append(total / len(perm))
    hist["acc_tr"].append(acc_tr); hist["acc_te"].append(acc_te)
    print(f"  {ep:>7}{total/len(perm):>11.4f}{acc_tr:>15.3f}{acc_te:>14.3f}{seg:>8.1f}")

seg_cnn = time.perf_counter() - t_entren
acc_cnn = hist["acc_te"][-1]
acc_cnn_tr = hist["acc_tr"][-1]

print()
print(f"  La CNN entrenó completa en {seg_cnn:.1f} segundos, en CPU, sin tarjeta gráfica.")
print("  Lea la columna 'Pérdida' bajando: eso es la red corrigiéndose. Cuando deja")
print("  de bajar, ya aprendió lo que podía con estos datos.")

# ===========================================================================
# 4. EL RESULTADO EN GERENCIAL
# ===========================================================================
titulo("EL RESULTADO")
print(f"  Accuracy de la CNN : {acc_cnn:.3f}  ->  de cada 100 láminas, "
      f"clasificó bien {acc_cnn*100:.0f}")
if acc_clasico is not None:
    print(f"  Accuracy del clásico: {acc_clasico:.3f}  ->  de cada 100 láminas, "
          f"clasificó bien {acc_clasico*100:.0f}")
    dif = (acc_cnn - acc_clasico) * 100
    print()
    print(f"  DIFERENCIA: {dif:+.1f} puntos a favor de la convolución.")
    print("  Los dos vieron exactamente las mismas imágenes y el mismo examen.")
    print("  Lo único que cambió fue MIRAR VECINDARIOS en vez de píxeles sueltos.")
    print()
    print("  Y aquí está el argumento gerencial completo, en dos frases:")
    print("     Con una tabla de Excel de 2.000 filas, el Random Forest le gana a la")
    print("     red -- y es más barato y más explicable.")
    print("     Con imágenes, audio o texto, la red gana y no hay discusión.")
    print("     No se deje vender redes neuronales para problemas de Excel.")

print()
print("  LA LETRA MENUDA, y hay que decirla siempre:")
print(f"  este {acc_cnn:.2f} es sobre imágenes SINTÉTICAS. Las dibujó un script, y por eso")
print("  los defectos salen limpios y siempre parecidos. Con fotos de verdad -- reflejos,")
print("  polvo en el lente, la lámina torcida, la luz del turno de la noche -- el número")
print("  BAJA, y baja harto. Un acierto casi perfecto en un laboratorio no es una promesa")
print("  de planta: es el piso desde el cual se empieza a trabajar.")
print("  Si en su proyecto de grado le sale 0.99 con datos reales, desconfíe primero.")
print()
print(f"  Control de overfitting: acierto en estudio {acc_cnn_tr:.3f} vs. "
      f"en examen {acc_cnn:.3f} (brecha {acc_cnn_tr-acc_cnn:+.3f}).")
if acc_cnn_tr - acc_cnn > 0.10:
    print("  ATENCIÓN: la brecha pasó de 0.10. La red se está memorizando las")
    print("  imágenes. Bájele épocas o consiga más imágenes.")
else:
    print("  Brecha pequeña: la red generaliza. Está aprendiendo, no memorizando.")

# Matriz de confusión y cobertura por clase
red.eval()
with torch.no_grad():
    pred = red(Tte).argmax(1).numpy()
cm = np.zeros((n_clases, n_clases), dtype=int)
for real, p in zip(yte, pred):
    cm[real, p] += 1

sub("Matriz de confusión · qué defecto confunde con qué")
enc = "  " + " " * 20 + "".join(f"{('dijo ' + c):>15}" for c in CLASES)
print(enc)
print("  " + "-" * 80)
for i, c in enumerate(CLASES):
    fila = "".join(f"{cm[i, j]:>15}" for j in range(n_clases))
    print(f"  {('era ' + c):<20}{fila}")

print()
print("  Cobertura por clase (Recall) - de cada 100 láminas de ese tipo, cuántas cazó:")
for i, c in enumerate(CLASES):
    rec = cm[i, i] / cm[i].sum() if cm[i].sum() else 0.0
    barra = "#" * int(round(rec * 34))
    print(f"     {c:<12}{rec*100:>6.1f} %   {barra}")

peor = int(np.argmin([cm[i, i] / max(1, cm[i].sum()) for i in range(n_clases)]))
print()
print(f"  La clase donde más falla es '{CLASES[peor]}'.")
print("  En una planta eso se traduce en una pregunta concreta: ¿cuál error me")
print("  cuesta más, dejar pasar una lámina mala (llega al cliente) o devolver una")
print("  buena (pierdo producción)? Con esa respuesta se ajusta el modelo.")
print()
print("  DISEÑO DEL PIPELINE: la alerta manda la lámina a REVISIÓN HUMANA.")
print("  El modelo no bota vidrio solo. Eso también es una decisión gerencial.")

# ===========================================================================
# 5. LA GRÁFICA
# ===========================================================================
fig = plt.figure(figsize=(13.6, 5.6), facecolor=CREMA)
tit = f"Control de calidad de vidrio · CNN   Accuracy {acc_cnn:.2f}"
if acc_clasico is not None:
    tit += f"   ·   modelo clásico píxel por píxel {acc_clasico:.2f}"
fig.suptitle(tit, fontsize=13.5, color=NAVY, y=0.97)

gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 1.0], wspace=0.30)

ax1 = fig.add_subplot(gs[0, 0]); ax1.set_facecolor("white")
ax1.plot(hist["epoca"], hist["acc_tr"], marker="o", ms=4, color=AZUL,
         label="Acierto en estudio")
ax1.plot(hist["epoca"], hist["acc_te"], marker="o", ms=4, color=ORO, linewidth=2.4,
         label="Acierto en examen")
if acc_clasico is not None:
    ax1.axhline(acc_clasico, color=ROJO, linestyle="--", linewidth=1.8,
                label=f"Clásico píxel a píxel ({acc_clasico:.2f})")
ax1.axhline(0.25, color="#7A8797", linestyle=":", linewidth=1.4,
            label="Adivinar al azar (0.25)")
ax1.set_xlabel("Época (repaso completo)", fontsize=9.5, color=NAVY)
ax1.set_ylabel("Accuracy", fontsize=9.5, color=NAVY)
ax1.set_ylim(0.0, 1.03)
ax1.set_title("Cómo aprendió, época por época", fontsize=11, color=NAVY, pad=10)
ax1.legend(fontsize=8.2, frameon=False, loc="lower right")
ax1.grid(color="#DDD8CC", linewidth=0.7); ax1.set_axisbelow(True)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

ax2 = fig.add_subplot(gs[0, 1]); ax2.set_facecolor("white")
ax2.imshow(cm, cmap="Blues", vmin=0)
ax2.set_xticks(range(n_clases), CLASES, fontsize=8.6, rotation=30, ha="right")
ax2.set_yticks(range(n_clases), CLASES, fontsize=8.6)
for i in range(n_clases):
    for j in range(n_clases):
        ax2.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=10.5,
                 color="white" if cm[i, j] > cm.max() * 0.55 else NAVY,
                 fontweight="bold" if i == j else "normal")
ax2.set_xlabel("El modelo dijo", fontsize=9.5, color=NAVY)
ax2.set_ylabel("En realidad era", fontsize=9.5, color=NAVY)
ax2.set_title("Matriz de confusión\n(la diagonal son los aciertos)",
              fontsize=11, color=NAVY, pad=10)
for s in ax2.spines.values():
    s.set_visible(False)

# Los errores: mostrar láminas que la red clasificó mal
ax3 = fig.add_subplot(gs[0, 2]); ax3.axis("off")
ax3.set_title("En qué se equivocó (láminas del examen)",
              fontsize=11, color=NAVY, pad=10)
errores = np.where(pred != yte)[0][:6]
if len(errores) == 0:
    ax3.text(0.5, 0.5, "No se equivocó en ninguna\nde las imágenes del examen",
             ha="center", va="center", fontsize=10, color=TEAL)
else:
    for k, e in enumerate(errores):
        sub_ax = ax3.inset_axes([0.03 + (k % 3) * 0.325, 0.52 - (k // 3) * 0.46,
                                 0.29, 0.40])
        sub_ax.imshow(Xte[e], cmap="gray", vmin=0, vmax=1)
        sub_ax.set_xticks([]); sub_ax.set_yticks([])
        sub_ax.set_title(f"era {CLASES[yte[e]]}\ndijo {CLASES[pred[e]]}",
                         fontsize=7.6, color=ROJO, pad=3)

fig.text(0.5, 0.015,
         "Imágenes sintéticas con semilla fija · Diplomado en Inteligencia Artificial · UNAC · Clase 05",
         ha="center", fontsize=8.5, color="#7A8797")
fig.tight_layout(rect=(0, 0.035, 1, 0.90))
salida = os.path.join(AQUI, ARCHIVO_GRAFICA)
fig.savefig(salida, dpi=130, facecolor=CREMA)
plt.close(fig)

total = time.perf_counter() - t_inicio
titulo("LISTO")
print(f"  Gráfica guardada en : {salida}")
print(f"  Entrenamiento CNN   : {seg_cnn:.1f} segundos")
if seg_clasico is not None:
    print(f"  Entrenamiento clásico: {seg_clasico:.1f} segundos")
print(f"  Tiempo total del script (incluye cargar PyTorch): {total:.1f} segundos")
print()
print("  Para usar SUS imágenes: pídale a Claude que le arme el .npz a partir de")
print("  una carpeta con subcarpetas, una por clase. Con 200 fotos por clase ya")
print("  se puede intentar. Regla de la casa: sus fotos se quedan en su computador.")
print("=" * 78)
print()
