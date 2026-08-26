# -*- coding: utf-8 -*-
"""
Plantilla 1 - Machine Learning SUPERVISADO
La pregunta de negocio: ¿esta factura se va a pagar tarde?

Tres modelos compiten (la escalera de la Clase 04, versión de bolsillo):
   Logistic Regression   -> la línea recta, de 1958, y todavía manda en los bancos
   Decision Tree         -> preguntas en cascada; se puede leer y auditar
   Random Forest         -> 300 árboles votando; sabiduría de multitudes

Imprime Accuracy, Precision, Recall y F1 Score explicados en español, la matriz de
confusión casilla por casilla, qué variables mira el modelo, y guarda una gráfica PNG.

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
matplotlib.use("Agg")          # sin ventanas: guarda la gráfica en archivo
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
ARCHIVO_CSV = "cartera_clientes.csv"
COLUMNA_OBJETIVO = "pago_tarde"       # la pregunta que el modelo aprende
COLUMNAS_A_IGNORAR = ["factura_id"]   # identificadores: nunca entran al modelo
PORCENTAJE_EXAMEN = 0.25              # 25 % de las filas se guardan para el examen
SEMILLA = 42
ARCHIVO_GRAFICA = "resultado_supervisado.png"
# ---------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVY, CREMA, ORO = "#0E2036", "#F6F5F0", "#EAAD05"
TEAL, ROJO, AZUL = "#29AC8A", "#D54E48", "#3C7FD0"

for f in ("Segoe UI", "DejaVu Sans"):
    try:
        plt.rcParams["font.family"] = [f]
        break
    except Exception:
        pass

t_inicio = time.perf_counter()


def titulo(txt):
    print()
    print("=" * 78)
    print("  " + txt)
    print("=" * 78)


def sub(txt):
    print()
    print("-- " + txt + " " + "-" * max(0, 74 - len(txt)))


# ===========================================================================
# 1. LOS DATOS
# ===========================================================================
ruta = os.path.join(AQUI, ARCHIVO_CSV)
if not os.path.exists(ruta):
    print(f"No encontré {ARCHIVO_CSV}. Lo genero ahora...")
    subprocess.run([sys.executable, os.path.join(AQUI, "1_generar_datos.py")], check=True)

df = pd.read_csv(ruta, encoding="utf-8-sig")

titulo("PLANTILLA 1 · MACHINE LEARNING SUPERVISADO")
print("  Pregunta de negocio : ¿esta factura se va a pagar TARDE?")
print("  Tipo de problema    : clasificación binaria (sí / no)")
print(f"  Filas               : {len(df)}     Columnas: {df.shape[1]}")
print("  Datos               : SINTÉTICOS, semilla fija (no son de ninguna empresa real)")

n_tarde = int(df[COLUMNA_OBJETIVO].sum())
print()
print(f"  De las {len(df)} facturas históricas, {n_tarde} se pagaron tarde "
      f"({n_tarde/len(df)*100:.1f} %) y {len(df)-n_tarde} a tiempo.")
print("  Ese es el balance de clases: si una clase fuera el 98 %, el Accuracy engañaría")
print("  (un modelo que siempre diga 'a tiempo' acertaría 98 veces de 100 sin saber nada).")

# ===========================================================================
# 2. TRAIN / TEST SPLIT — «el examen con preguntas que nadie vio»
# ===========================================================================
X = df.drop(columns=[COLUMNA_OBJETIVO] + COLUMNAS_A_IGNORAR)
y = df[COLUMNA_OBJETIVO].astype(int)

# Detección de columnas de texto vs. numéricas.
# OJO: en pandas 3.x las columnas de texto YA NO son dtype 'object' (son 'str'),
# así que el chequeo clásico `X[c].dtype == object` falla en silencio. Se usa
# is_numeric_dtype, que funciona igual en pandas 2.x y 3.x.
num = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
cat = [c for c in X.columns if c not in num]

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=PORCENTAJE_EXAMEN, random_state=SEMILLA, stratify=y)

sub("train/test split · partir los datos")
print(f"  Estudia con : {len(X_tr)} facturas   ({(1-PORCENTAJE_EXAMEN)*100:.0f} %)")
print(f"  Se examina  : {len(X_te)} facturas   ({PORCENTAJE_EXAMEN*100:.0f} %) "
      "-- estas NO las vio nunca")
print("  Todas las métricas de abajo salen del examen. Nunca del estudio.")
print("  Si el acierto de estudio es altísimo y el de examen malo, eso es OVERFITTING")
print("  (sobreajuste): el modelo se memorizó el cuaderno en vez de aprender.")

pre = ColumnTransformer([
    ("categoricas", OneHotEncoder(handle_unknown="ignore"), cat),
    ("numericas", StandardScaler(), num),
])

MODELOS = {
    "Logistic Regression": LogisticRegression(max_iter=2000, random_state=SEMILLA),
    "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=SEMILLA),
    "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=8,
                                            random_state=SEMILLA, n_jobs=-1),
}

# ===========================================================================
# 3. LA COMPETENCIA
# ===========================================================================
sub("La competencia · tres modelos, el mismo examen")
print("  Accuracy  (acierto total)  de cada 100 facturas, en cuántas acertó")
print("  Precision (precisión)      de las que marcó como 'se atrasa', cuántas se atrasaron")
print("  Recall    (cobertura)      de las que sí se atrasaron, cuántas alcanzó a marcar")
print("  F1 Score  (equilibrio)     una sola nota que promedia Precision y Recall")
print()

filas, entrenados = [], {}
for nombre, modelo in MODELOS.items():
    pipe = Pipeline([("preparar", pre), ("modelo", modelo)])
    t0 = time.perf_counter()
    pipe.fit(X_tr, y_tr)
    seg = time.perf_counter() - t0
    p_te = pipe.predict(X_te)
    p_tr = pipe.predict(X_tr)
    filas.append({
        "Modelo": nombre,
        "Accuracy": accuracy_score(y_te, p_te),
        "Precision": precision_score(y_te, p_te, zero_division=0),
        "Recall": recall_score(y_te, p_te, zero_division=0),
        "F1 Score": f1_score(y_te, p_te, zero_division=0),
        "Acc. estudio": accuracy_score(y_tr, p_tr),
        "Segundos": seg,
    })
    entrenados[nombre] = pipe

tabla = pd.DataFrame(filas).sort_values("F1 Score", ascending=False).reset_index(drop=True)

anchos = f"{'':>3}{'Modelo':<22}{'Accuracy':>10}{'Precision':>11}{'Recall':>9}{'F1 Score':>10}{'seg':>7}"
print(anchos)
print("  " + "-" * 74)
for i, r in tabla.iterrows():
    medalla = ["1.", "2.", "3."][i] if i < 3 else "  "
    print(f"{medalla:>3}{r['Modelo']:<22}{r['Accuracy']:>10.3f}{r['Precision']:>11.3f}"
          f"{r['Recall']:>9.3f}{r['F1 Score']:>10.3f}{r['Segundos']:>7.2f}")

campeon_nombre = tabla.loc[0, "Modelo"]
campeon = entrenados[campeon_nombre]
acc = tabla.loc[0, "Accuracy"]
prec = tabla.loc[0, "Precision"]
rec = tabla.loc[0, "Recall"]
f1v = tabla.loc[0, "F1 Score"]
acc_est = tabla.loc[0, "Acc. estudio"]

print()
print(f"  CAMPEÓN: {campeon_nombre}")
print()
print(f"  Accuracy  {acc:.2f}  ->  de cada 100 facturas, acertó en {acc*100:.0f}.")
print(f"  Precision {prec:.2f}  ->  de cada 100 que marcó como riesgosas, "
      f"{prec*100:.0f} se atrasaron de verdad;")
print(f"                     las otras {100-prec*100:.0f} fueron llamadas de cobranza gastadas de más.")
print(f"  Recall    {rec:.2f}  ->  de cada 100 que sí se atrasaron, alcanzó a avisar de "
      f"{rec*100:.0f};")
print(f"                     se le escaparon {100-rec*100:.0f} sin que nadie las llamara.")
print(f"  F1 Score  {f1v:.2f}  ->  la nota de equilibrio entre los dos errores.")
print()
print(f"  Control de overfitting: acierto en estudio {acc_est:.3f} vs. en examen {acc:.3f} "
      f"(brecha {acc_est-acc:+.3f}).")
if acc_est - acc > 0.10:
    print("  ATENCIÓN: brecha mayor a 0.10 -> el modelo se está memorizando. Bájele profundidad.")
else:
    print("  Brecha pequeña: el modelo generaliza. Está aprendiendo, no memorizando.")
print()
print("  Ninguno debería dar 1.00. Si algún día le da 1.00, no celebre: revise si se le")
print("  filtró al modelo una columna que ya contiene la respuesta.")

# ===========================================================================
# 4. MATRIZ DE CONFUSIÓN — la gráfica del gerente
# ===========================================================================
pred = campeon.predict(X_te)
cm = confusion_matrix(y_te, pred)
vn, fp, fn, vp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]

sub("Matriz de confusión · dónde se equivoca, y cuánto cuesta cada error")
print(f"  Sobre las {len(y_te)} facturas del examen:")
print()
print(f"  {vp:>5}  ACIERTOS ÚTILES     dijo 'se atrasa' y se atrasó "
      "-> cobranza preventiva que sirvió")
print(f"  {vn:>5}  ACIERTOS TRANQUILOS dijo 'paga a tiempo' y pagó "
      "-> no se molestó al cliente")
print(f"  {fp:>5}  FALSA ALARMA        dijo 'se atrasa' y pagó bien "
      "-> costo: una llamada de más, roce con un buen cliente")
print(f"  {fn:>5}  SE LE ESCAPÓ        dijo 'paga a tiempo' y se atrasó "
      "-> costo: plata quieta, la que de verdad duele")
print()
monto_prom = df["monto_factura"].mean()
print(f"  Traducido a plata (monto promedio de factura ${monto_prom:,.0f}):".replace(",", "."))
print(f"     las {fn} que se le escaparon representan ~${fn*monto_prom:,.0f} "
      "en cartera sin alertar.".replace(",", "."))
print(f"     las {fp} falsas alarmas representan {fp} llamadas de cobranza innecesarias.")
print()
print("  DECISIÓN GERENCIAL: los dos errores NO cuestan igual. Si la plata quieta duele")
print("  más que una llamada de más, se sube el Recall a costa de la Precision (se baja el")
print("  umbral de alerta). Eso lo decide usted, no el modelo.")

# ===========================================================================
# 4b. LA PERILLA DEL GERENTE — mover el umbral
# ===========================================================================
sub("La perilla del gerente · mover el umbral de alerta")
print("  El modelo no dice 'sí' o 'no': dice una PROBABILIDAD. El 'sí' aparece cuando")
print("  esa probabilidad pasa un umbral, y el umbral por defecto (50 %) no es sagrado.")
print("  Bajarlo = alertar más = atrapar más atrasos y gastar más llamadas.")
print()
proba = campeon.predict_proba(X_te)[:, 1]
print(f"  {'Umbral':>8}{'Alertadas':>11}{'Precision':>11}{'Recall':>9}{'F1 Score':>10}"
      f"{'Se escapan':>12}")
print("  " + "-" * 74)
for u in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70):
    pu = (proba >= u).astype(int)
    marca = "  <- por defecto" if abs(u - 0.50) < 1e-9 else ""
    print(f"  {u:>8.2f}{int(pu.sum()):>11}{precision_score(y_te, pu, zero_division=0):>11.3f}"
          f"{recall_score(y_te, pu, zero_division=0):>9.3f}"
          f"{f1_score(y_te, pu, zero_division=0):>10.3f}"
          f"{int(((pu == 0) & (y_te == 1)).sum()):>12}{marca}")
print()
print("  Lea la tabla como un presupuesto: '¿cuántas llamadas de cobranza al mes puedo")
print("  pagar?' define el umbral. NO es una pregunta técnica; es una pregunta de gerencia.")
print("  Es el mismo modelo en todas las filas: lo único que cambió fue la perilla.")

# ===========================================================================
# 5. QUÉ MIRA EL MODELO
# ===========================================================================
sub("Qué variables mira el modelo para decidir")
nombres = list(campeon.named_steps["preparar"].get_feature_names_out())
nombres = [n.split("__", 1)[-1] for n in nombres]
mod = campeon.named_steps["modelo"]
if hasattr(mod, "feature_importances_"):
    imp = mod.feature_importances_
    etiqueta = "importancia"
else:
    imp = np.abs(mod.coef_[0])
    imp = imp / imp.sum() if imp.sum() else imp
    etiqueta = "peso (coeficiente absoluto normalizado)"
orden = np.argsort(imp)[::-1][:8]
print(f"  Top 8 por {etiqueta}:")
for i in orden:
    barra = "#" * max(1, int(round(imp[i] / imp[orden[0]] * 34)))
    print(f"    {nombres[i]:<34}{imp[i]:6.3f}  {barra}")
print()
print("  Léalo así: eso es lo que el modelo aprendió a mirar. Si la variable más")
print("  importante le parece absurda, el problema está en los datos, no en el modelo.")

# ===========================================================================
# 6. UN CASO NUEVO
# ===========================================================================
sub("Ponerlo a trabajar · una factura que llega mañana")
nueva = pd.DataFrame([{
    "canal": "Tienda de barrio", "zona": "Costa", "antiguedad_meses": 7,
    "dias_credito_pactado": 15, "monto_factura": 2_400_000, "facturas_previas": 6,
    "pct_pagos_tarde_previo": 0.62, "dias_atraso_promedio_previo": 27.5,
    "tiene_acuerdo_pago": 1, "descuento_pct": 6.0, "mes": 9,
}])[X.columns]
p = campeon.predict_proba(nueva)[0, 1]
print("  Cliente nuevo: tienda de barrio en la Costa, 7 meses de relación,")
print("  crédito a 15 días, $2.400.000, 62 % de sus pagos anteriores fueron tarde.")
print()
print(f"  Probabilidad de atraso que le asigna el modelo: {p*100:.1f} %")
print(f"  Con umbral 50 % la decisión es: "
      f"{'LLAMAR ANTES DEL VENCIMIENTO' if p >= 0.5 else 'dejarlo seguir su curso'}")
print()
print("  Así se ve la IA metida DENTRO del proceso: no un informe, una decisión que")
print("  se toma sola todos los días. Ese es el trabajo DE IA de la regla del pipeline.")

# ===========================================================================
# 7. LA GRÁFICA
# ===========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), facecolor=CREMA)
fig.suptitle(f"Cartera · ¿esta factura se paga tarde?   Campeón: {campeon_nombre}   "
             f"Accuracy {acc:.2f}  ·  F1 {f1v:.2f}",
             fontsize=13.5, color=NAVY, y=0.97)

ax1.set_facecolor("white")
im = ax1.imshow(cm, cmap="Blues", vmin=0)
etiq = ["Pagó a tiempo", "Se atrasó"]
ax1.set_xticks([0, 1], ["El modelo dijo\na tiempo", "El modelo dijo\nse atrasa"], fontsize=9.5)
ax1.set_yticks([0, 1], ["Realidad:\npagó a tiempo", "Realidad:\nse atrasó"], fontsize=9.5)
textos = [["Acierto tranquilo", "Falsa alarma"], ["Se le escapó", "Acierto útil"]]
for i in range(2):
    for j in range(2):
        color = "white" if cm[i, j] > cm.max() * 0.55 else NAVY
        ax1.text(j, i - 0.10, f"{cm[i, j]}", ha="center", va="center",
                 fontsize=22, color=color, fontweight="bold")
        ax1.text(j, i + 0.22, textos[i][j], ha="center", va="center",
                 fontsize=8.5, color=color)
ax1.set_title("Matriz de confusión (Confusion Matrix)\nsobre las facturas del examen",
              fontsize=11, color=NAVY, pad=10)
for s in ax1.spines.values():
    s.set_visible(False)

ax2.set_facecolor("white")
top = orden[::-1]
ax2.barh([nombres[i][:30] for i in top], [imp[i] for i in top], color=ORO,
         edgecolor=NAVY, linewidth=0.6)
ax2.set_title(f"Qué mira el modelo ({etiqueta})", fontsize=11, color=NAVY, pad=10)
ax2.tick_params(labelsize=9)
ax2.grid(axis="x", color="#DDD8CC", linewidth=0.7)
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

total = time.perf_counter() - t_inicio
titulo("LISTO")
print(f"  Gráfica guardada en : {salida}")
print(f"  Tiempo total        : {total:.1f} segundos")
print()
print("  Para usar SUS datos: reemplace cartera_clientes.csv por su archivo, ajuste")
print("  COLUMNA_OBJETIVO en el panel de control, y pídale a Claude que lo corra.")
print("  Regla de la casa: datos de su empresa se quedan en su computador.")
print("=" * 78)
print()
