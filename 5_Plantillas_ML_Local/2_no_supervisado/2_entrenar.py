# -*- coding: utf-8 -*-
r"""
Plantilla 2 - AUTOENCODER sobre datos (deteccion de anomalias)
La pregunta de negocio: de estos 3.000 pagos, cuales 30 debo mirar yo primero.

COMO FUNCIONA UN AUTOENCODER, EN DOS MINUTOS
   Es una red neuronal con forma de reloj de arena. Entra un pago con sus 10
   caracteristicas, la red lo APRIETA hasta 4 numeros (el cuello del reloj, el
   "espacio latente") y despues intenta RECONSTRUIR el pago original a partir
   de esos 4 numeros.

      10 datos  ->  32  ->  16  ->  8  ->  4  ->  8  ->  16  ->  32  ->  10 datos
                  \_____ encoder _____/       \_____ decoder _____/

   Se entrena SOLO con pagos normales. Entonces la red se vuelve experta en
   reconstruir lo normal, y nada mas. Cuando le llega un pago raro, no logra
   reconstruirlo: el error de reconstruccion se dispara. Ese error es el
   puntaje de sospecha.

   No hay etiquetas. Nadie le dijo cual era raro. Por eso es NO SUPERVISADO.

EL PIPELINE - los cinco pasos, marcados en el codigo de abajo
   1 DATOS         leer el CSV
   2 PREPARACION   one-hot a las columnas de texto + escalar todo a 0-1
   3 ENTRENAMIENTO la red aprende a reconstruir SOLO lo normal
   4 EVALUACION    umbral, matriz de confusion, y la perilla del gerente
   5 RESULTADO     la lista de trabajo del auditor en CSV + la grafica PNG

   LA PRUEBA DEL BORRADO: si usted le quita la IA a este proceso y le queda un
   auditor revisando 3.000 filas a mano en Excel, la IA NO era decoracion: le
   entrego una lista priorizada de 30. Si le queda el mismo auditor haciendo lo
   mismo y la lista se guarda en un cajon, si era decoracion.

ENTORNO - IMPORTANTE
   Esta plantilla corre en el ENTORNO 2 (torch). NO corre en el entorno de
   PyCaret y no debe intentarse: PyCaret exige numpy 1.x y torch exige numpy 2.x.
   Ver 0_instalar.txt.

Datos SINTETICOS. Ver 1_generar_datos.py.
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

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
ARCHIVO_CSV = "movimientos_contables.csv"
COLUMNAS_A_IGNORAR = ["movimiento_id"]          # identificadores: nunca entran
COLUMNA_VERIFICACION = "es_anomalia"            # LA TRAMPA: solo para calificar.
#                                                 CON SUS DATOS: póngala en None.
COLUMNA_PATRON = "patron_sembrado"              # idem, solo para el informe final.
#                                                 CON SUS DATOS: póngala en None.
PORCENTAJE_EXAMEN = 0.30      # % de los pagos NORMALES que se guarda para el examen
CUELLO_LATENTE = 4            # a cuántos números se aprieta cada pago
EPOCAS = 150                  # cuántas veces la red repasa todos los pagos normales
TAMANO_LOTE = 128
TASA_APRENDIZAJE = 0.004
K_DESVIACIONES = 1.5          # umbral = promedio + K x desviación del error normal
#                               La receta clásica del notebook de la maestría es
#                               K = 1.0. Aquí quedó en 1.5 porque la tabla de la
#                               "perilla del gerente" mostró que equilibra mejor.
#                               Súbala para levantar menos; bájela para levantar más.
CUANTOS_REVISAR = 30          # el tamaño de la lista de trabajo del auditor
SEMILLA = 11
ARCHIVO_GRAFICA = "resultado_autoencoder.png"
ARCHIVO_SALIDA = "movimientos_revisados.csv"
# ---------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVY, CREMA, ORO = "#0E2036", "#F6F5F0", "#EAAD05"
TEAL, ROJO, AZUL = "#29AC8A", "#D54E48", "#3C7FD0"


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
# 0. ¿ESTÁN LAS LIBRERÍAS?
# ===========================================================================
try:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")           # sin ventanas: guarda la gráfica en archivo
    import matplotlib.pyplot as plt
    import torch
    import torch.nn as nn
    from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
    from sklearn.compose import ColumnTransformer
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                                 f1_score, confusion_matrix)
except ImportError as e:
    print()
    print("=" * 78)
    print("  FALTA UNA LIBRERÍA DEL ENTORNO 2")
    print("=" * 78)
    print(f"  Python no encontró: {e.name}")
    print()
    print("  Esta plantilla corre en el ENTORNO 2 (el de torch), el mismo de la")
    print("  plantilla 3. Se corre escribiendo su Python completo:")
    print()
    print("      C:\\ia\\env_deep\\Scripts\\python.exe 2_entrenar.py")
    print()
    print("  NO se corre con 'py' ni con 'python' a secas.")
    print()
    print("  Si todavía no lo ha creado, la receta completa está en")
    print("  0_instalar.txt (PASO 2). En resumen:")
    print()
    print("      py -m venv C:\\ia\\env_deep")
    print("      C:\\ia\\env_deep\\Scripts\\python.exe -m pip install torch "
          "scikit-learn pandas matplotlib numpy")
    print()
    print("  OJO: NO instale PyCaret en este entorno ni torch en el de PyCaret.")
    print("  Se rompen entre ellos (PyCaret exige numpy 1.x; torch exige numpy 2.x).")
    print("=" * 78)
    print()
    sys.exit(1)

for f in ("Segoe UI", "DejaVu Sans"):
    try:
        plt.rcParams["font.family"] = [f]
        break
    except Exception:
        pass

torch.manual_seed(SEMILLA)
np.random.seed(SEMILLA)

# ===========================================================================
# 1. LOS DATOS  ·  paso 1 del pipeline
# ===========================================================================
ruta = os.path.join(AQUI, ARCHIVO_CSV)
if not os.path.exists(ruta):
    print(f"No encontré {ARCHIVO_CSV}. Lo genero ahora...")
    subprocess.run([sys.executable, os.path.join(AQUI, "1_generar_datos.py")], check=True)

df = pd.read_csv(ruta, encoding="utf-8-sig")

titulo("PLANTILLA 2 · AUTOENCODER · DETECCIÓN DE ANOMALÍAS EN PAGOS")
print("  Pregunta de negocio : de estos pagos, ¿cuáles debo mirar yo primero?")
print("  Tipo de problema    : detección de anomalías, NO SUPERVISADO")
print(f"  Filas               : {len(df)}     Columnas: {df.shape[1]}")
print("  Datos               : SINTÉTICOS, semilla fija (no son de ninguna entidad real)")
print(f"  PyTorch             : {torch.__version__}   ·   corriendo en CPU con "
      f"{torch.get_num_threads()} hilos")
print("  Tarjeta gráfica     : NO se necesita")

# ===========================================================================
# 2. PREPARACIÓN  ·  paso 2 del pipeline
# ===========================================================================
# ¿Trae el CSV una columna de respuesta para poder calificar al final?
# Con los datos de ejemplo: sí (la sembramos). Con los datos de una empresa
# real: casi nunca. El script funciona en los dos casos.
TIENE_VERIFICACION = (COLUMNA_VERIFICACION is not None
                      and COLUMNA_VERIFICACION in df.columns)
TIENE_PATRON = (TIENE_VERIFICACION and COLUMNA_PATRON is not None
                and COLUMNA_PATRON in df.columns)

fuera = list(COLUMNAS_A_IGNORAR) + [COLUMNA_VERIFICACION, COLUMNA_PATRON]
X = df.drop(columns=[c for c in fuera if c is not None and c in df.columns])

if TIENE_VERIFICACION:
    y_real = df[COLUMNA_VERIFICACION].astype(int).to_numpy()
else:
    # Sin etiquetas se asume que la inmensa mayoría de las filas es normal
    # (que es cierto: las anomalías son raras por definición) y se entrena con
    # todo. Es exactamente como se usa esta técnica en la vida real.
    y_real = np.zeros(len(df), dtype=int)
patron = (df[COLUMNA_PATRON].astype(str).to_numpy() if TIENE_PATRON
          else np.array(["-"] * len(df)))

# Detección de columnas de texto vs. numéricas.
# OJO: en pandas 3.x las columnas de texto YA NO son dtype 'object' (son 'str'),
# así que el chequeo clásico `X[c].dtype == object` falla en silencio. Se usa
# is_numeric_dtype, que funciona igual en pandas 2.x y 3.x.
num = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
cat = [c for c in X.columns if c not in num]

sub("Preparación · dejar todo en números entre 0 y 1")
print(f"  Columnas numéricas ({len(num)}) : {', '.join(num)}")
print(f"  Columnas de texto  ({len(cat)}) : {', '.join(cat) if cat else '(ninguna)'}")
print()
print("  Dos cosas obligatorias antes de que una red neuronal pueda mirar una tabla:")
print("  1. ONE-HOT a las columnas de texto: 'Efectivo' no es un número, así que se")
print("     convierte en columnas de sí/no (una por cada valor posible).")
print("  2. ESCALAR todo al rango 0-1. Sin esto, el 'monto' (millones) aplastaría al")
print("     'num_aprobadores' (1 a 5) y la red solo aprendería a mirar el monto.")
print("     Aquí es obligatorio, no opcional: la última capa es una sigmoid, que")
print("     por definición solo puede producir valores entre 0 y 1.")

pre = ColumnTransformer([
    ("categoricas", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
    ("numericas", MinMaxScaler(), num),
])

# ---------------------------------------------------------------------------
# EL SPLIT DE UN AUTOENCODER, QUE NO ES EL SPLIT DE LA PLANTILLA 1
# La red se entrena SOLO con movimientos normales. Los raros no entran nunca al
# entrenamiento: si entraran, la red aprendería a reconstruirlos bien y dejaría
# de levantarlos. Es la idea central de la técnica.
# El examen sí lleva de los dos: los normales que se guardaron + TODOS los raros.
# ---------------------------------------------------------------------------
idx_normal = np.where(y_real == 0)[0]
idx_anomalo = np.where(y_real == 1)[0]

idx_tr, idx_te_normal = train_test_split(
    idx_normal, test_size=PORCENTAJE_EXAMEN, random_state=SEMILLA)
idx_te = np.concatenate([idx_te_normal, idx_anomalo])
rng = np.random.default_rng(SEMILLA)
rng.shuffle(idx_te)

X_tr_df = X.iloc[idx_tr]
X_te_df = X.iloc[idx_te]

# El escalador se AJUSTA solo con los datos de entrenamiento. Si se ajustara con
# todo, los movimientos raros del examen le habrían "contado" al modelo cuál es
# el máximo del monto. Eso es fuga de información (data leakage).
X_tr = pre.fit_transform(X_tr_df).astype(np.float32)
X_te = pre.transform(X_te_df).astype(np.float32)
y_te = y_real[idx_te]
patron_te = patron[idx_te]
n_entradas = X_tr.shape[1]

sub("El split · la red solo ve lo normal")
print(f"  Entrena con : {len(idx_tr)} movimientos, TODOS normales")
print(f"  Se examina  : {len(idx_te)} movimientos "
      f"({len(idx_te_normal)} normales + {len(idx_anomalo)} raros)")
print(f"  Entradas de la red : {n_entradas} "
      f"({len(num)} numéricas + {n_entradas - len(num)} columnas one-hot)")
print()
print("  Los raros NO entran al entrenamiento. Si entraran, la red aprendería a")
print("  reconstruirlos bien y dejaría de levantarlos. Ahí está toda la técnica.")

# ===========================================================================
# 3. ENTRENAMIENTO  ·  paso 3 del pipeline
# ===========================================================================
CAPAS = [32, 16, 8]


class Autoencoder(nn.Module):
    """El reloj de arena: aprieta hasta CUELLO_LATENTE y vuelve a abrir."""

    def __init__(self, n_in, cuello):
        super().__init__()
        capas_enc, prev = [], n_in
        for h in CAPAS:
            capas_enc += [nn.Linear(prev, h), nn.ReLU()]
            prev = h
        capas_enc += [nn.Linear(prev, cuello), nn.ReLU()]
        self.encoder = nn.Sequential(*capas_enc)

        capas_dec, prev = [], cuello
        for h in reversed(CAPAS):
            capas_dec += [nn.Linear(prev, h), nn.ReLU()]
            prev = h
        # sigmoid al final porque los datos están escalados entre 0 y 1
        capas_dec += [nn.Linear(prev, n_in), nn.Sigmoid()]
        self.decoder = nn.Sequential(*capas_dec)

    def forward(self, x):
        return self.decoder(self.encoder(x))


modelo = Autoencoder(n_entradas, CUELLO_LATENTE)
n_params = sum(p.numel() for p in modelo.parameters())

sub("La arquitectura · el reloj de arena")
print(f"  {n_entradas} -> " + " -> ".join(str(c) for c in CAPAS) +
      f" -> [{CUELLO_LATENTE}] -> " + " -> ".join(str(c) for c in reversed(CAPAS)) +
      f" -> {n_entradas}")
print(f"  Parámetros que la red ajusta : {n_params:,}".replace(",", "."))
print(f"  Función de pérdida           : MAE (error absoluto medio)")
print(f"  Optimizador                  : Adam, tasa de aprendizaje {TASA_APRENDIZAJE}")
print()
print(f"  El cuello de {CUELLO_LATENTE} números es la restricción que hace que esto")
print("  funcione. Si el cuello fuera igual de ancho que la entrada, la red copiaría")
print("  y pegaría sin aprender nada, y todos los errores serían cero.")

Xtr_t = torch.from_numpy(X_tr)
Xte_t = torch.from_numpy(X_te)
opt = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE)
criterio = nn.L1Loss()          # L1Loss = MAE, el mismo del notebook del docente

sub(f"Entrenamiento · {EPOCAS} épocas sobre {len(idx_tr)} movimientos normales")
print("  Una ÉPOCA es una pasada completa por todos los datos. En cada pasada la red")
print("  compara lo que reconstruyó contra lo que entró, mide el error, y corrige sus")
print("  parámetros para equivocarse menos la próxima vez. Eso es entrenar.")
print()
hist_tr, hist_te = [], []
n = len(Xtr_t)
t0 = time.perf_counter()
for ep in range(1, EPOCAS + 1):
    modelo.train()
    orden = torch.randperm(n)
    total = 0.0
    for i in range(0, n, TAMANO_LOTE):
        lote = Xtr_t[orden[i:i + TAMANO_LOTE]]
        opt.zero_grad()
        perdida = criterio(modelo(lote), lote)
        perdida.backward()
        opt.step()
        total += perdida.item() * len(lote)
    hist_tr.append(total / n)

    modelo.eval()
    with torch.no_grad():
        hist_te.append(criterio(modelo(Xte_t), Xte_t).item())

    if ep == 1 or ep % 25 == 0 or ep == EPOCAS:
        print(f"    época {ep:>4}/{EPOCAS}   error entrenamiento {hist_tr[-1]:.5f}"
              f"   error examen {hist_te[-1]:.5f}")
seg_entrenamiento = time.perf_counter() - t0
print()
print(f"  Entrenamiento terminado en {seg_entrenamiento:.1f} segundos, en CPU.")
print(f"  El error de entrenamiento bajó de {hist_tr[0]:.5f} a {hist_tr[-1]:.5f} "
      f"({(1 - hist_tr[-1] / hist_tr[0]) * 100:.0f} % menos).")

# ===========================================================================
# 4. EVALUACIÓN  ·  paso 4 del pipeline
# ===========================================================================
modelo.eval()
with torch.no_grad():
    err_tr = torch.mean(torch.abs(modelo(Xtr_t) - Xtr_t), dim=1).numpy()
    err_te = torch.mean(torch.abs(modelo(Xte_t) - Xte_t), dim=1).numpy()

umbral = float(err_tr.mean() + K_DESVIACIONES * err_tr.std())

sub("El umbral · dónde se corta entre 'normal' y 'raro'")
print("  El autoencoder no dice 'raro' ni 'normal': entrega un ERROR DE")
print("  RECONSTRUCCIÓN por cada movimiento. El corte lo pone usted.")
print()
print(f"  Error promedio en los normales de entrenamiento : {err_tr.mean():.5f}")
print(f"  Desviación estándar de ese error               : {err_tr.std():.5f}")
print(f"  UMBRAL = promedio + {K_DESVIACIONES} x desviación         : {umbral:.5f}")
print()
print("  Por encima del umbral = 'revíselo'. Es la misma receta del notebook de la")
print("  maestría del docente: media del error de entrenamiento más una desviación.")

pred = (err_te >= umbral).astype(int)
print()
print(f"  Con ese umbral se levantan {int(pred.sum())} de los {len(pred)} movimientos "
      f"del examen ({pred.mean()*100:.1f} %).")

if not TIENE_VERIFICACION:
    # ---------------------------------------------------------------------
    # CAMINO SIN ETIQUETAS - el caso real de una empresa
    # ---------------------------------------------------------------------
    acc = prec = rec = f1v = float("nan")
    cm = None
    sub("Sin columna de respuesta · no hay métricas, y está bien")
    print("  Usted no tiene una columna que diga cuáles movimientos estaban raros.")
    print("  Entonces NO se puede calcular Accuracy, Precision ni Recall: no hay contra")
    print("  qué comparar. Eso no es una falla del modelo; es la naturaleza del problema.")
    print()
    print("  Lo que sí tiene, y es lo que vale:")
    print("  - una lista de sus movimientos ordenada de más sospechoso a menos;")
    print("  - un umbral que usted mueve según cuántos pueda revisar.")
    print()
    print("  CÓMO SE VALIDA ESTO EN LA VIDA REAL: se toman los 30 primeros de la lista,")
    print("  se los pasa a quien sabe del tema (el auditor, el contador, el almacenista)")
    print("  y se le pregunta cuántos de esos 30 le parecen efectivamente raros. Ese")
    print("  número -- dicho por un humano que sabe -- es su Precision. No hay atajo.")

    sub("La perilla del gerente · mover el umbral")
    print("  El mismo modelo entregado, sin reentrenar nada, cambiando solo el corte:")
    print()
    print(f"  {'K':>5}{'Umbral':>10}{'Levantados':>12}{'% del total':>13}")
    print("  " + "-" * 42)
    for k in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        u = float(err_tr.mean() + k * err_tr.std())
        pk = (err_te >= u).astype(int)
        marca = "  <- el que quedó" if abs(k - K_DESVIACIONES) < 1e-9 else ""
        print(f"  {k:>5.1f}{u:>10.5f}{int(pk.sum()):>12}"
              f"{pk.mean()*100:>12.1f} %{marca}")
    print()
    print("  Lea la columna 'Levantados' como un presupuesto de horas de auditoría.")
    print("  '¿Cuántos movimientos al mes puede revisar mi equipo?' define K. NO es una")
    print("  pregunta técnica; es una pregunta de gerencia.")
else:
    acc = accuracy_score(y_te, pred)
    prec = precision_score(y_te, pred, zero_division=0)
    rec = recall_score(y_te, pred, zero_division=0)
    f1v = f1_score(y_te, pred, zero_division=0)
    cm = confusion_matrix(y_te, pred)
    vn, fp, fn, vp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]

    sub("Las métricas · aquí sí hay con qué calificar, porque sembramos la respuesta")
    print(f"  Error promedio de los {int((y_te == 0).sum())} movimientos NORMALES del examen : "
          f"{err_te[y_te == 0].mean():.5f}")
    print(f"  Error promedio de los {int((y_te == 1).sum())} movimientos RAROS del examen   : "
          f"{err_te[y_te == 1].mean():.5f}")
    razon = err_te[y_te == 1].mean() / err_te[y_te == 0].mean()
    print(f"  Los raros le cuestan {razon:.1f} veces más trabajo de reconstruir. "
          "Eso es la señal.")
    print()
    print(f"  Accuracy  {acc:.3f}   de cada 100 movimientos, clasificó bien {acc*100:.0f}")
    print(f"  Precision {prec:.3f}   de cada 100 que levantó, {prec*100:.0f} estaban raros de verdad")
    print(f"  Recall    {rec:.3f}   de cada 100 raros que había, alcanzó a levantar {rec*100:.0f}")
    print(f"  F1 Score  {f1v:.3f}   la nota de equilibrio entre los dos")
    print()
    print("  OJO CON EL ACCURACY EN ANOMALÍAS: solo el "
          f"{(y_te == 1).mean()*100:.0f} % del examen está raro. Un modelo")
    print("  que dijera 'todo normal' sacaría "
          f"{(1-(y_te == 1).mean())*100:.0f} % de Accuracy sin servir para nada.")
    print("  En detección de anomalías el Accuracy es el número menos útil de los cuatro.")
    print("  Mire Recall (cuántos raros atrapó) y Precision (cuánto tiempo del auditor gastó).")

    sub("Matriz de confusión · los dos errores no cuestan lo mismo")
    print(f"  Sobre los {len(y_te)} movimientos del examen:")
    print()
    print(f"  {vp:>5}  ATRAPADOS         estaba raro y lo levantó "
          "-> el hallazgo, para lo que se hizo todo esto")
    print(f"  {vn:>5}  DEJADOS PASAR OK  estaba bien y no lo tocó "
          "-> no se le gastó tiempo al auditor")
    print(f"  {fp:>5}  FALSA ALARMA      estaba bien y lo levantó "
          "-> costo: el auditor revisa un pago sano")
    print(f"  {fn:>5}  SE LE ESCAPÓ      estaba raro y no lo vio "
          "-> costo: el hallazgo que nadie encontró")
    print()
    print("  DECISIÓN GERENCIAL: una falsa alarma cuesta 20 minutos de un auditor. Un")
    print("  pago raro que se escapa puede costar el hallazgo de una auditoría externa.")
    print("  Si no cuestan igual, el umbral no debe quedar en el valor por defecto.")

    sub("Qué patrón sí atrapó y cuál se le escapa")
    print("  Los raros venían de cuatro patrones sembrados. Desagregado:")
    print()
    print(f"    {'Patrón sembrado':<36}{'Había':>7}{'Atrapó':>8}{'Recall':>9}")
    print("    " + "-" * 60)
    for p in sorted(set(patron_te[y_te == 1])):
        m = (y_te == 1) & (patron_te == p)
        hay = int(m.sum())
        atr = int((pred[m] == 1).sum())
        print(f"    {p:<36}{hay:>7}{atr:>8}{atr/hay if hay else 0:>9.2f}")
    print()
    print("  Esta tabla es la más útil para el negocio: dice QUÉ TIPO de irregularidad")
    print("  el modelo ve bien y cuál no. Si un patrón queda en Recall bajo, ese patrón")
    print("  se sigue revisando a mano, y se dice en el informe. No se esconde.")

    sub("La perilla del gerente · mover el umbral")
    print("  El mismo modelo entregado, sin reentrenar nada, cambiando solo el corte:")
    print()
    print(f"  {'K':>5}{'Umbral':>10}{'Levantados':>12}{'Precision':>11}{'Recall':>9}"
          f"{'F1':>8}{'Se escapan':>12}")
    print("  " + "-" * 72)
    for k in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        u = float(err_tr.mean() + k * err_tr.std())
        pk = (err_te >= u).astype(int)
        marca = "  <- el que quedó" if abs(k - K_DESVIACIONES) < 1e-9 else ""
        print(f"  {k:>5.1f}{u:>10.5f}{int(pk.sum()):>12}"
              f"{precision_score(y_te, pk, zero_division=0):>11.3f}"
              f"{recall_score(y_te, pk, zero_division=0):>9.3f}"
              f"{f1_score(y_te, pk, zero_division=0):>8.3f}"
              f"{int(((pk == 0) & (y_te == 1)).sum()):>12}{marca}")
    print()
    print("  Lea la columna 'Levantados' como un presupuesto de horas de auditoría.")
    print("  '¿Cuántos pagos al mes puede revisar mi equipo?' define K. NO es una")
    print("  pregunta técnica; es una pregunta de gerencia.")

# ===========================================================================
# 5. RESULTADO  ·  paso 5 del pipeline
# ===========================================================================
sub(f"La lista de trabajo · los {CUANTOS_REVISAR} que se revisan el lunes")
salida = df.iloc[idx_te].copy()
salida["error_reconstruccion"] = err_te
salida["puntaje_sospecha"] = np.round(err_te / umbral, 3)
salida["se_levanta"] = pred
salida = salida.sort_values("error_reconstruccion", ascending=False)

ruta_salida = os.path.join(AQUI, ARCHIVO_SALIDA)
salida.to_csv(ruta_salida, index=False, encoding="utf-8-sig")

top = salida.head(CUANTOS_REVISAR)
if TIENE_VERIFICACION:
    aciertos_top = int(top[COLUMNA_VERIFICACION].sum())
    esperado_azar = (y_te == 1).mean() * CUANTOS_REVISAR
    print(f"  De los {CUANTOS_REVISAR} movimientos con más error de reconstrucción, "
          f"{aciertos_top} estaban")
    print(f"  sembrados como raros ({aciertos_top/CUANTOS_REVISAR*100:.0f} % de la lista).")
    print(f"  Al azar, en un examen con {(y_te == 1).mean()*100:.0f} % de raros, se habría "
          f"esperado {esperado_azar:.0f}.")
    if esperado_azar > 0:
        print(f"  El modelo concentró {aciertos_top/esperado_azar:.1f} veces más hallazgos "
              "en la misma cantidad de horas de auditoría.")
else:
    print(f"  Los {CUANTOS_REVISAR} movimientos con más error de reconstrucción quedaron")
    print("  de primeros en el archivo. Empiece por arriba: ese es el orden de revisión.")
print()
print("  Los 8 primeros de la lista (las columnas propias de sus datos, más el puntaje):")
print()
# Preview genérico: sirva con las columnas que sea, no solo con las del ejemplo.
cols_vista = ([c for c in COLUMNAS_A_IGNORAR if c in salida.columns][:1]
              + [c for c in X.columns][:4]
              + ["puntaje_sospecha"])
cols_vista = list(dict.fromkeys(cols_vista))
with pd.option_context("display.width", 200, "display.max_columns", 50):
    print(salida[cols_vista].head(8).to_string(index=False))
print()
print(f"  Archivo completo : {ruta_salida}")
print("  Se abre con doble clic en Excel, ya ordenado de más sospechoso a menos.")
print("  Columnas que le agregó el modelo: error_reconstruccion, puntaje_sospecha")
print("  (error dividido por el umbral: arriba de 1.00 es 'revíselo') y se_levanta.")
print("  ESE archivo es el entregable. No el modelo: la lista.")

# ---------------------------------------------------------------------------
# LA GRÁFICA
# ---------------------------------------------------------------------------
if TIENE_VERIFICACION:
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.6, 5.0), facecolor=CREMA)
    fig.suptitle(f"Autoencoder · detección de anomalías   ·   Recall {rec:.2f}  ·  "
                 f"Precision {prec:.2f}  ·  {len(idx_tr)} normales de entrenamiento",
                 fontsize=13, color=NAVY, y=0.97)
else:
    # Sin etiquetas no hay matriz de confusión que dibujar: quedan dos paneles.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 5.0), facecolor=CREMA)
    ax3 = None
    fig.suptitle(f"Autoencoder · detección de anomalías   ·   "
                 f"{int(pred.sum())} movimientos levantados de {len(pred)}   ·   "
                 f"{len(idx_tr)} filas de entrenamiento",
                 fontsize=13, color=NAVY, y=0.97)

# 1) la curva de entrenamiento
ax1.set_facecolor("white")
ax1.plot(hist_tr, color=AZUL, linewidth=1.8, label="Entrenamiento (solo normales)")
ax1.plot(hist_te, color=ORO, linewidth=1.6, label="Examen (normales + raros)")
ax1.set_title("Cómo bajó el error, época por época", fontsize=10.5, color=NAVY, pad=9)
ax1.set_xlabel("Época", fontsize=9)
ax1.set_ylabel("Error de reconstrucción (MAE)", fontsize=9)
ax1.legend(fontsize=8.5, frameon=False)
ax1.grid(color="#DDD8CC", linewidth=0.7)
ax1.set_axisbelow(True)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# 2) los dos histogramas de error, con el umbral
ax2.set_facecolor("white")
bins = np.linspace(0, float(np.percentile(err_te, 99.5)), 45)
if TIENE_VERIFICACION:
    ax2.hist(err_te[y_te == 0], bins=bins, color=TEAL, alpha=0.85, label="Normales")
    ax2.hist(err_te[y_te == 1], bins=bins, color=ROJO, alpha=0.85,
             label="Raros (sembrados)")
else:
    ax2.hist(err_te, bins=bins, color=TEAL, alpha=0.85, label="Todos los movimientos")
ax2.axvline(umbral, color=NAVY, linestyle="--", linewidth=1.8)
ax2.text(umbral, ax2.get_ylim()[1] * 0.92, f" umbral {umbral:.4f}", fontsize=8.5,
         color=NAVY)
ax2.set_title("Error de reconstrucción · la separación", fontsize=10.5, color=NAVY, pad=9)
ax2.set_xlabel("Error por movimiento", fontsize=9)
ax2.set_ylabel("Cuántos movimientos", fontsize=9)
ax2.legend(fontsize=8.5, frameon=False)
ax2.grid(axis="y", color="#DDD8CC", linewidth=0.7)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

# 3) la matriz de confusión (solo si hay con qué calificar)
if ax3 is not None:
    ax3.set_facecolor("white")
    ax3.imshow(cm, cmap="Blues", vmin=0)
    ax3.set_xticks([0, 1], ["No lo\nlevantó", "Lo\nlevantó"], fontsize=9.5)
    ax3.set_yticks([0, 1], ["Realidad:\nestaba bien", "Realidad:\nestaba raro"],
                   fontsize=9.5)
    textos = [["Pasó OK", "Falsa alarma"], ["Se le escapó", "Atrapado"]]
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > cm.max() * 0.55 else NAVY
            ax3.text(j, i - 0.10, f"{cm[i, j]}", ha="center", va="center",
                     fontsize=20, color=color, fontweight="bold")
            ax3.text(j, i + 0.22, textos[i][j], ha="center", va="center",
                     fontsize=8.5, color=color)
    ax3.set_title("Matriz de confusión (Confusion Matrix)", fontsize=10.5,
                  color=NAVY, pad=9)
    for s in ax3.spines.values():
        s.set_visible(False)

fig.text(0.5, 0.015,
         "Datos sintéticos con semilla fija · Diplomado en Inteligencia Artificial · "
         "UNAC · Clase 05",
         ha="center", fontsize=8.5, color="#7A8797")
fig.tight_layout(rect=(0, 0.035, 1, 0.92))
ruta_grafica = os.path.join(AQUI, ARCHIVO_GRAFICA)
fig.savefig(ruta_grafica, dpi=125, facecolor=CREMA)
plt.close(fig)

total = time.perf_counter() - t_inicio
titulo("LISTO")
print(f"  Gráfica guardada en : {ruta_grafica}")
print(f"  Lista de trabajo    : {ruta_salida}")
print(f"  Tiempo total        : {total:.1f} segundos "
      f"(entrenamiento: {seg_entrenamiento:.1f} s)")
print()
print("  PARA USAR SUS DATOS:")
print("  1. Ponga su CSV en esta carpeta y cambie ARCHIVO_CSV en el panel de control.")
print("  2. Ponga en COLUMNAS_A_IGNORAR los identificadores (código, cédula, NIT...).")
print("  3. Si usted NO tiene una columna de respuesta -- lo normal en la vida real --")
print("     deje COLUMNA_VERIFICACION = None. El script salta las métricas y le")
print("     entrega igual la lista ordenada por sospecha, que es el entregable.")
print("  4. Pídale a Claude que lo corra. El prompt está en 3_prompt_para_claude.txt")
print()
print("  Regla de la casa: los datos de su empresa se quedan en su computador.")
print("=" * 78)
print()
