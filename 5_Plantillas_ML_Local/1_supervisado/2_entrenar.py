# -*- coding: utf-8 -*-
"""
===============================================================================
 PLANTILLA 1 - SUPERVISED LEARNING con PyCaret (AutoML)
 La pregunta de negocio: ¿esta factura se va a pagar tarde?
===============================================================================

QUE HACE ESTO, EN UNA FRASE
   Usted le entrega una tabla y le dice cual columna es la respuesta. PyCaret
   prepara los datos, entrena NUEVE modelos distintos, los compara con el mismo
   examen y le devuelve el campeon. Usted no escoge el modelo: el modelo se
   escoge solo. Eso es AutoML (Automated Machine Learning).

EL PIPELINE, QUE ES LO QUE HAY QUE APRENDERSE
   PASO 1  DATOS         ->  cartera_clientes.csv (4.000 facturas ya respondidas)
   PASO 2  PREPARACION   ->  setup()          PyCaret limpia, imputa y parte
   PASO 3  ENTRENAMIENTO ->  compare_models() nueve modelos compiten
   PASO 4  EVALUACION    ->  predict_model()  el examen que nadie vio
   PASO 5  RESULTADO     ->  modelo_cartera.pkl + resultado_supervisado.png

   Ese orden no se cambia. Es el mismo de la plantilla 2 y de la plantilla 3.

-------------------------------------------------------------------------------
 ENTORNO - LEA ESTO ANTES DE CORRER
-------------------------------------------------------------------------------
   Esta plantilla corre en el entorno env_pycaret y SOLO ahi:

       C:\\ia\\env_pycaret\\Scripts\\python.exe 2_entrenar.py

   PyCaret exige versiones viejas de numpy y scikit-learn. Si se instala en el
   mismo entorno que PyTorch (plantillas 2 y 3) las rompe. Por eso son dos
   entornos separados. Ver 0_instalar.txt.

-------------------------------------------------------------------------------
 CONTRATO PARA UN AGENTE DE IA que adapte esta plantilla a datos reales
-------------------------------------------------------------------------------
   SE PUEDE CAMBIAR (y solo esto):
      El bloque PANEL DE CONTROL de abajo: ARCHIVO_CSV, COLUMNA_OBJETIVO,
      COLUMNAS_A_IGNORAR, PORCENTAJE_EXAMEN, MODELOS_A_COMPARAR, METRICA_ORDEN,
      SEMILLA, y el diccionario FACTURA_NUEVA del PASO 5.

   NO SE DEBE TOCAR:
      El orden de los cinco pasos. El uso de setup() antes de compare_models().
      El hecho de que las metricas finales salgan de predict_model() y NUNCA
      de la tabla de compare_models() (esa es validacion cruzada, no examen).

   QUE ESPERA EL ARCHIVO DE ENTRADA:
      - Un CSV con encabezado en la primera fila, codificado utf-8.
      - Una fila por caso (una factura, un paciente, un contrato, un producto).
      - Una columna de respuesta ya conocida = COLUMNA_OBJETIVO. Para
        clasificacion binaria debe tener exactamente dos valores distintos
        (0/1, Si/No, True/False). PyCaret los codifica solo.
      - Las demas columnas pueden ser numeros o texto, mezclados. PyCaret hace
        one-hot encoding del texto y imputa los vacios sin que nadie se lo pida.
      - Minimo razonable: 300 filas y al menos 30 casos de la clase minoritaria.
        Por debajo de eso las metricas son ruido y hay que decirlo.

   VALIDACIONES OBLIGATORIAS ANTES DE ENTRENAR (el script las hace y aborta):
      1. Que el archivo exista.
      2. Que COLUMNA_OBJETIVO exista en el CSV.
      3. Que COLUMNA_OBJETIVO tenga 2 valores distintos (ni 1 ni 20).
      4. Que ninguna columna de COLUMNAS_A_IGNORAR falte (avisa y sigue).

   FUGA DE DATOS - la trampa que hay que revisar siempre:
      Toda columna que solo se conoce DESPUES de saber la respuesta debe ir en
      COLUMNAS_A_IGNORAR. Ejemplo: 'dias_de_atraso_de_esta_factura' contiene la
      respuesta. Si entra, el Accuracy sale en 1.00 y el modelo no sirve para
      nada en produccion. Un 1.00 no se celebra: se investiga.

   ERRORES COMUNES Y QUE SIGNIFICAN:
      "ModuleNotFoundError: No module named 'pycaret'"
          -> esta corriendo con el Python equivocado. Use el de env_pycaret.
      "ValueError: could not convert string to float"
          -> quedo texto en una columna que deberia ser numero (comas de miles,
             simbolo $, 'N/A'). Limpie la columna en el CSV, no en el script.
      "Target column has 1 unique value"
          -> el CSV filtrado quedo con una sola clase. No hay nada que aprender.
      Accuracy alto y Recall en 0.00
          -> clases muy desbalanceadas. Mire la tabla de umbrales del PASO 4;
             el problema es el umbral, no el modelo.

   REGLA DE LA CASA: los datos del estudiante se quedan en su computador.
   Este script no sube nada a ninguna parte y no debe modificarse para hacerlo.

===============================================================================
 Datos SINTETICOS con semilla fija. Ver 1_generar_datos.py.
 Diplomado en Inteligencia Artificial - UNAC - Clase 05
===============================================================================
"""

import sys
import os
import time
import subprocess
import warnings

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")

# ---------------------------------------------------------------------------
# PANEL DE CONTROL - aquí y solo aquí se cambian cosas
# ---------------------------------------------------------------------------
ARCHIVO_CSV = "cartera_clientes.csv"
COLUMNA_OBJETIVO = "pago_tarde"        # la columna con la respuesta ya conocida
COLUMNAS_A_IGNORAR = ["factura_id"]    # identificadores y fugas: nunca entran
PORCENTAJE_EXAMEN = 0.25               # 25 % de las filas se guardan para el examen
SEMILLA = 42                           # fíjela y todo el salón obtiene lo mismo

# Los nueve competidores del AutoML. Son los códigos que usa PyCaret.
#   lr = Logistic Regression      ridge = Ridge Classifier
#   dt = Decision Tree            rf = Random Forest
#   et = Extra Trees              gbc = Gradient Boosting
#   ada = AdaBoost                knn = K Neighbors        nb = Naive Bayes
# Si pone MODELOS_A_COMPARAR = None, PyCaret compara TODOS los que tenga.
# Ojo: incluir "lightgbm" funciona, pero escupe cientos de líneas de log en
# pantalla y le tapa el resultado. Por eso no está en la lista.
MODELOS_A_COMPARAR = ["lr", "ridge", "dt", "rf", "et", "gbc", "ada", "knn", "nb"]
METRICA_ORDEN = "F1"                   # con qué nota se ordena el podio
ARCHIVO_GRAFICA = "resultado_supervisado.png"
ARCHIVO_MODELO = "modelo_cartera"      # se guarda como modelo_cartera.pkl
# ---------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
NAVY, CREMA, ORO = "#0E2036", "#F6F5F0", "#EAAD05"
TEAL, ROJO, AZUL = "#29AC8A", "#D54E48", "#3C7FD0"

t_inicio = time.perf_counter()


def titulo(txt):
    print()
    print("=" * 78)
    print("  " + txt)
    print("=" * 78)


def sub(txt):
    print()
    print("-- " + txt + " " + "-" * max(0, 74 - len(txt)))


def morir(mensaje, arreglo):
    print()
    print("!" * 78)
    print("  NO PUEDO SEGUIR: " + mensaje)
    print()
    print("  QUÉ HACER: " + arreglo)
    print("!" * 78)
    sys.exit(1)


# ===========================================================================
# PASO 0 · EL ENTORNO CORRECTO
# ===========================================================================
try:
    import pandas as pd
    import numpy as np
except ImportError:
    morir("no encontré pandas ni numpy.",
          "corra:  C:\\ia\\env_pycaret\\Scripts\\python.exe -m pip install pycaret-core")

# PyCaret crea un archivo tecnico "logs.log" en la carpeta DE TRABAJO, en el
# momento de importarlo, y lo deja abierto (en Windows no se puede borrar
# despues). Para que no ensucie la carpeta de la plantilla, nos paramos en una
# carpeta temporal antes de importarlo y nos quedamos ahi. No hay riesgo: todo
# lo que este script lee y escribe usa rutas absolutas armadas sobre AQUI.
import tempfile
_TEMP_TRABAJO = tempfile.mkdtemp(prefix="pycaret_unac_")
try:
    os.chdir(_TEMP_TRABAJO)
except OSError:
    pass

try:
    from pycaret.classification import (setup, compare_models, pull, predict_model,
                                        finalize_model, save_model, get_config)
    import pycaret
except ImportError:
    morir("no encontré PyCaret en este Python.",
          "esta plantilla NO corre con el Python del sistema. Corra:\n"
          "             C:\\ia\\env_pycaret\\Scripts\\python.exe 2_entrenar.py\n"
          "             Si esa carpeta no existe, siga el PASO 1 de 0_instalar.txt.")

import matplotlib
matplotlib.use("Agg")               # sin ventanas: guarda la gráfica en archivo
import matplotlib.pyplot as plt

for familia in ("Segoe UI", "DejaVu Sans"):
    if any(familia == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = [familia]
        break

# ===========================================================================
# PASO 1 · LOS DATOS
# ===========================================================================
ruta = os.path.join(AQUI, ARCHIVO_CSV)
if not os.path.exists(ruta):
    print(f"No encontré {ARCHIVO_CSV}. Lo genero ahora...")
    subprocess.run([sys.executable, os.path.join(AQUI, "1_generar_datos.py")], check=True)

df = pd.read_csv(ruta, encoding="utf-8-sig")

titulo("PLANTILLA 1 · SUPERVISED LEARNING con PyCaret (AutoML)")
print("  Pregunta de negocio : ¿esta factura se va a pagar TARDE?")
print("  Tipo de problema    : clasificación binaria (sí / no)")
print(f"  Herramienta         : PyCaret {pycaret.__version__}  (AutoML)")
print(f"  Archivo             : {ARCHIVO_CSV}")
print(f"  Filas               : {len(df)}     Columnas: {df.shape[1]}")
print("  Datos               : SINTÉTICOS, semilla fija (no son de ninguna empresa real)")

# --- validaciones del contrato -------------------------------------------
if COLUMNA_OBJETIVO not in df.columns:
    morir(f"el CSV no tiene la columna objetivo '{COLUMNA_OBJETIVO}'.",
          "abra el CSV, mire cómo se llama de verdad la columna con la respuesta,\n"
          "             y escriba ese nombre en COLUMNA_OBJETIVO del PANEL DE CONTROL.\n"
          f"             Columnas disponibles: {', '.join(map(str, df.columns))}")

faltan = [c for c in COLUMNAS_A_IGNORAR if c not in df.columns]
if faltan:
    print(f"\n  AVISO: estas columnas de COLUMNAS_A_IGNORAR no están en el CSV y las omito: {faltan}")
ignorar = [c for c in COLUMNAS_A_IGNORAR if c in df.columns]

clases = df[COLUMNA_OBJETIVO].dropna().unique()
if len(clases) < 2:
    morir(f"la columna '{COLUMNA_OBJETIVO}' tiene un solo valor ({clases}).",
          "no hay nada que aprender: todos los casos son iguales. Revise el filtro\n"
          "             con que armó el CSV.")
if len(clases) > 2:
    morir(f"la columna '{COLUMNA_OBJETIVO}' tiene {len(clases)} valores distintos.",
          "esta plantilla es de clasificación BINARIA (dos respuestas posibles).\n"
          "             Agrupe sus categorías en dos, o pídale a Claude la versión multiclase.")

sub("Los datos · las primeras cinco filas, para que las mire")
print("  Nunca entrene con datos que no ha visto. Estas son cinco facturas de verdad")
print("  del archivo, tal como el modelo las va a recibir:")
print()
vista = df.drop(columns=ignorar, errors="ignore").head(5)
print(vista.to_string(index=False, max_colwidth=16))

n_si = int((df[COLUMNA_OBJETIVO] == sorted(clases)[-1]).sum())
print()
print(f"  Balance de clases: de las {len(df)} facturas históricas, {n_si} se pagaron "
      f"tarde ({n_si/len(df)*100:.1f} %)")
print(f"                     y {len(df)-n_si} a tiempo ({(len(df)-n_si)/len(df)*100:.1f} %).")
print("  Esto se mira ANTES de entrenar. Si una clase fuera el 98 %, el Accuracy")
print("  engañaría: un modelo que siempre diga 'a tiempo' acertaría 98 de 100 sin")
print("  saber nada. Con 32/68 estamos bien.")

# ===========================================================================
# PASO 2 · PREPARACIÓN — lo que PyCaret hace solo
# ===========================================================================
sub("PASO 2 · Preparación · setup() · lo que PyCaret hace sin que se lo pidan")
print("  Esta es la línea que reemplaza medio día de trabajo:")
print()
print(f"     setup(data=df, target='{COLUMNA_OBJETIVO}', train_size={1-PORCENTAJE_EXAMEN:.2f}, ...)")
print()
t0 = time.perf_counter()
setup(
    data=df,
    target=COLUMNA_OBJETIVO,
    ignore_features=ignorar,          # identificadores y fugas fuera
    train_size=1 - PORCENTAJE_EXAMEN,
    session_id=SEMILLA,               # la semilla: resultados reproducibles
    fold=10,                          # validación cruzada de 10 pliegues
    html=False,                       # estamos en consola, no en un notebook
    verbose=False,
    system_log=False,                 # sin archivo logs.log en la carpeta
    n_jobs=-1,
)
seg_setup = time.perf_counter() - t0
info = pull()
d = {str(r["Description"]): r["Value"] for _, r in info.iterrows()}


def dato(k, alt="?"):
    return d.get(k, alt)


print(f"  Listo en {seg_setup:.1f} segundos. Esto es lo que hizo, traducido:")
print()
print(f"    · Tomó la tabla de {dato('Original data shape')} y la dejó en "
      f"{dato('Transformed data shape')}")
print(f"      (crecieron las columnas porque convirtió el texto en números: one-hot encoding)")
print(f"    · Detectó solo cuáles columnas son números ({dato('Numeric features')}) y")
print(f"      cuáles son texto ({dato('Categorical features')}). Nadie se lo dijo.")
print(f"    · Rellenó los vacíos: en los números con el promedio "
      f"('{dato('Numeric imputation')}'), en el texto con el valor más frecuente "
      f"('{dato('Categorical imputation')}').")
print(f"    · Partió los datos:  ESTUDIO {dato('Transformed train set shape')}   "
      f"EXAMEN {dato('Transformed test set shape')}")
print(f"    · Dejó armada la validación cruzada: {dato('Fold Generator')} de "
      f"{dato('Fold Number')} pliegues.")
print(f"    · GPU: {dato('Use GPU')}. Todo esto corre en el procesador de su computador.")
print()
print("  DOS PARTICIONES QUE NO SON LO MISMO, y aquí se confunde todo el mundo:")
print("    EXAMEN (holdout)  -> las facturas apartadas. NADIE las toca hasta el PASO 4.")
print("    VALIDACIÓN CRUZADA-> dentro del estudio, parte en 10, entrena con 9 y prueba")
print("                         con 1, diez veces. Sirve para ELEGIR el modelo (PASO 3).")
print("  Se elige con validación cruzada. Se reporta con el examen. Nunca al revés.")

# ===========================================================================
# PASO 3 · ENTRENAMIENTO — el AutoML
# ===========================================================================
n_comp = "todos los disponibles" if MODELOS_A_COMPARAR is None else len(MODELOS_A_COMPARAR)
sub(f"PASO 3 · Entrenamiento · compare_models() · {n_comp} modelos compiten")
print("  Otra línea, y aquí está el corazón del AutoML:")
print()
print(f"     best = compare_models(sort='{METRICA_ORDEN}')")
print()
print("  PyCaret entrena cada modelo diez veces (los diez pliegues), le saca el")
print("  promedio, y los ordena. Usted no escoge el algoritmo: el algoritmo se")
print("  escoge solo, con evidencia. Eso es lo que hace un AutoML.")
print()
t0 = time.perf_counter()
kwargs = dict(sort=METRICA_ORDEN, round=4, verbose=False)
if MODELOS_A_COMPARAR is not None:
    kwargs["include"] = MODELOS_A_COMPARAR
mejor = compare_models(**kwargs)
seg_entrenar = time.perf_counter() - t0
podio = pull()

print(f"  Los {len(podio)} modelos entrenados y comparados en {seg_entrenar:.1f} segundos.")
print("  (Promedios de la validación cruzada de 10 pliegues, NO del examen todavía.)")
print()
cols = [c for c in ("Model", "Accuracy", "AUC", "Recall", "Prec.", "F1", "TT (Sec)")
        if c in podio.columns]
print(f"  {'':>4}{'Modelo':<32}{'Accuracy':>10}{'AUC':>8}{'Recall':>8}{'Prec.':>8}{'F1':>8}{'seg':>8}")
print("  " + "-" * 76)
for i, (_, r) in enumerate(podio.iterrows()):
    medalla = ["1.", "2.", "3."][i] if i < 3 else "  "
    print(f"  {medalla:>3} {str(r['Model'])[:31]:<32}{r.get('Accuracy', 0):>10.3f}"
          f"{r.get('AUC', 0):>8.3f}{r.get('Recall', 0):>8.3f}{r.get('Prec.', 0):>8.3f}"
          f"{r.get('F1', 0):>8.3f}{r.get('TT (Sec)', 0):>8.2f}")

campeon_nombre = str(podio.iloc[0]["Model"])
print()
print(f"  CAMPEÓN DEL AUTOML: {campeon_nombre}")
print(f"  Clase de Python por debajo: {type(mejor).__name__}")
print()
print("  Mire la última columna. El campeón se entrenó en menos de un segundo. El")
print("  cuento de que 'entrenar IA cuesta millones' es cierto para modelos como")
print("  Claude o GPT, no para el 90 % de los problemas de una empresa. Lo caro de")
print("  un proyecto de IA nunca es el entrenamiento: son los datos.")

# ===========================================================================
# PASO 4 · EVALUACIÓN — el examen que nadie vio
# ===========================================================================
sub("PASO 4 · Evaluación · predict_model() · el examen que nadie vio")
print("  Hasta aquí todo salió de la validación cruzada. Ahora sí se abre el sobre")
print("  sellado del PASO 2: las facturas que ningún modelo tocó nunca.")
print()
holdout = predict_model(mejor, verbose=False, raw_score=True)
metricas = pull()
m = {c: float(metricas.iloc[0][c]) for c in metricas.columns if c != "Model"}

acc = m.get("Accuracy", 0.0)
prec = m.get("Prec.", 0.0)
rec = m.get("Recall", 0.0)
f1v = m.get("F1", 0.0)
auc = m.get("AUC", 0.0)
acc_cv = float(podio.iloc[0].get("Accuracy", 0.0))

print("  Las cuatro notas, y qué significa cada una en facturas:")
print()
print(f"  Accuracy  {acc:.3f}  ->  de cada 100 facturas del examen, acertó en {acc*100:.0f}.")
print(f"  Precision {prec:.3f}  ->  de cada 100 que marcó como riesgosas, {prec*100:.0f} se")
print(f"                       atrasaron de verdad; las otras {100-prec*100:.0f} fueron llamadas")
print(f"                       de cobranza gastadas de más.")
print(f"  Recall    {rec:.3f}  ->  de cada 100 que sí se atrasaron, alcanzó a avisar de")
print(f"                       {rec*100:.0f}; se le escaparon {100-rec*100:.0f} sin que nadie las llamara.")
print(f"  F1 Score  {f1v:.3f}  ->  una sola nota que equilibra las dos anteriores.")
print(f"  AUC       {auc:.3f}  ->  qué tan bien ordena de más riesgoso a menos riesgoso.")
print("                       0.50 es tirar una moneda; 1.00 es perfecto.")
print()
print(f"  Control de overfitting: validación cruzada {acc_cv:.3f}  vs.  examen {acc:.3f}"
      f"   (brecha {acc_cv-acc:+.3f})")
if abs(acc_cv - acc) > 0.10:
    print("  ATENCIÓN: brecha mayor a 0.10. El modelo se está memorizando el cuaderno.")
    print("  Eso es OVERFITTING (sobreajuste): bájele complejidad o consiga más datos.")
else:
    print("  Brecha pequeña: el modelo generaliza. Está aprendiendo, no memorizando.")
print()
print("  Ninguna nota debería dar 1.000. Si algún día le da 1.000, no celebre:")
print("  revise si se le filtró al modelo una columna que ya contiene la respuesta.")
print("  Eso se llama fuga de datos (data leakage) y es el error número uno.")

# --- matriz de confusión --------------------------------------------------
y_real = holdout[COLUMNA_OBJETIVO].astype(int).to_numpy()
y_pred = holdout["prediction_label"].astype(int).to_numpy()
vn = int(((y_real == 0) & (y_pred == 0)).sum())
fp = int(((y_real == 0) & (y_pred == 1)).sum())
fn = int(((y_real == 1) & (y_pred == 0)).sum())
vp = int(((y_real == 1) & (y_pred == 1)).sum())
cm = np.array([[vn, fp], [fn, vp]])

sub("Matriz de confusión · dónde se equivoca, y cuánto cuesta cada error")
print(f"  Sobre las {len(y_real)} facturas del examen:")
print()
print(f"  {vp:>5}  ACIERTOS ÚTILES     dijo 'se atrasa' y se atrasó "
      "-> cobranza preventiva que sirvió")
print(f"  {vn:>5}  ACIERTOS TRANQUILOS dijo 'paga a tiempo' y pagó "
      "-> no se molestó al cliente")
print(f"  {fp:>5}  FALSA ALARMA        dijo 'se atrasa' y pagó bien "
      "-> costo: una llamada de más")
print(f"  {fn:>5}  SE LE ESCAPÓ        dijo 'paga a tiempo' y se atrasó "
      "-> costo: plata quieta")
print()
if "monto_factura" in df.columns:
    monto_prom = float(df["monto_factura"].mean())
    print(f"  Traducido a plata (monto promedio de factura ${monto_prom:,.0f}):".replace(",", "."))
    print(f"     las {fn} que se le escaparon representan ~${fn*monto_prom:,.0f} "
          "en cartera sin alertar.".replace(",", "."))
    print(f"     las {fp} falsas alarmas representan {fp} llamadas de cobranza innecesarias.")
    print()
print("  DECISIÓN GERENCIAL: los dos errores NO cuestan igual. Si la plata quieta")
print("  duele más que una llamada de más, se sube el Recall a costa de la Precision.")
print("  Eso lo decide usted, no el modelo. Y se hace con la perilla de abajo.")

# --- la perilla del gerente ----------------------------------------------
sub("La perilla del gerente · mover el umbral de alerta")
print("  El modelo no dice 'sí' o 'no': dice una PROBABILIDAD. El 'sí' aparece cuando")
print("  esa probabilidad pasa un umbral, y el umbral por defecto (0.50) no es sagrado.")
print("  Bajarlo = alertar más = atrapar más atrasos y gastar más llamadas.")
print()
proba = holdout["prediction_score_1"].to_numpy(dtype=float)
print(f"  {'Umbral':>8}{'Alertadas':>11}{'Precision':>11}{'Recall':>9}{'F1 Score':>10}"
      f"{'Se escapan':>12}")
print("  " + "-" * 74)
for u in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70):
    pu = (proba >= u).astype(int)
    tp = int(((y_real == 1) & (pu == 1)).sum())
    fpu = int(((y_real == 0) & (pu == 1)).sum())
    fnu = int(((y_real == 1) & (pu == 0)).sum())
    p_u = tp / (tp + fpu) if (tp + fpu) else 0.0
    r_u = tp / (tp + fnu) if (tp + fnu) else 0.0
    f_u = 2 * p_u * r_u / (p_u + r_u) if (p_u + r_u) else 0.0
    marca = "  <- por defecto" if abs(u - 0.50) < 1e-9 else ""
    print(f"  {u:>8.2f}{int(pu.sum()):>11}{p_u:>11.3f}{r_u:>9.3f}{f_u:>10.3f}{fnu:>12}{marca}")
print()
print("  Lea la tabla como un presupuesto: '¿cuántas llamadas de cobranza al mes")
print("  puedo pagar?' define el umbral. NO es una pregunta técnica; es una pregunta")
print("  de gerencia. Es el MISMO modelo en todas las filas: lo único que cambió")
print("  fue la perilla. Aquí es donde el gerente manda sobre la IA.")

# --- qué mira el modelo ---------------------------------------------------
sub("Qué variables mira el modelo para decidir")
try:
    nombres = list(get_config("X_train_transformed").columns)
    if hasattr(mejor, "feature_importances_"):
        imp = np.asarray(mejor.feature_importances_, dtype=float)
        etiqueta = "importancia"
    elif hasattr(mejor, "coef_"):
        imp = np.abs(np.asarray(mejor.coef_, dtype=float).ravel())
        imp = imp / imp.sum() if imp.sum() else imp
        etiqueta = "peso (coeficiente absoluto normalizado)"
    else:
        imp, etiqueta = None, None
    if imp is not None and len(imp) == len(nombres):
        orden = np.argsort(imp)[::-1][:8]
        print(f"  Top 8 por {etiqueta}:")
        for i in orden:
            barra = "#" * max(1, int(round(imp[i] / max(imp[orden[0]], 1e-9) * 34)))
            print(f"    {nombres[i][:34]:<34}{imp[i]:6.3f}  {barra}")
    else:
        orden = None
        print(f"  El modelo campeón ({campeon_nombre}) no publica importancias de variables.")
except Exception as e:
    orden, nombres, imp, etiqueta = None, [], None, None
    print(f"  No pude extraer las importancias ({type(e).__name__}). No es grave.")
print()
print("  Léalo así: eso es lo que el modelo aprendió a mirar. Si la variable más")
print("  importante le parece absurda, el problema está en los datos, no en el modelo.")

# ===========================================================================
# PASO 5 · RESULTADO — el modelo puesto a trabajar
# ===========================================================================
sub("PASO 5 · Resultado · finalize_model() · el modelo listo para producción")
print("  finalize_model() vuelve a entrenar el campeón con TODAS las filas, examen")
print("  incluido. Se hace de último, cuando ya no hay nada que medir, para no")
print("  desperdiciar datos. El archivo .pkl que sale es el entregable: eso es lo")
print("  que se le pasa a un sistema para que prediga solo, todos los días.")
final = finalize_model(mejor)
save_model(final, os.path.join(AQUI, ARCHIVO_MODELO), verbose=False)
pkl = os.path.join(AQUI, ARCHIVO_MODELO + ".pkl")
print(f"  Guardado: {ARCHIVO_MODELO}.pkl  ({os.path.getsize(pkl)/1024:.0f} KB)")

sub("Ponerlo a trabajar · una factura que llega mañana")
FACTURA_NUEVA = {
    "canal": "Tienda de barrio", "zona": "Costa", "antiguedad_meses": 7,
    "dias_credito_pactado": 15, "monto_factura": 2_400_000, "facturas_previas": 6,
    "pct_pagos_tarde_previo": 0.62, "dias_atraso_promedio_previo": 27.5,
    "tiene_acuerdo_pago": 1, "descuento_pct": 6.0, "mes": 9,
}
print("  Cliente: tienda de barrio en la Costa, 7 meses de relación, crédito a")
print("  15 días, $2.400.000, y 62 % de sus pagos anteriores fueron tarde.")
print()
try:
    nueva = pd.DataFrame([FACTURA_NUEVA])
    r = predict_model(final, data=nueva, raw_score=True, verbose=False)
    p = float(r["prediction_score_1"].iloc[0])
    print(f"  Probabilidad de atraso que le asigna el modelo: {p*100:.1f} %")
    print(f"  Con umbral 0.50 la decisión es: "
          f"{'LLAMAR ANTES DEL VENCIMIENTO' if p >= 0.5 else 'dejarlo seguir su curso'}")
except Exception as e:
    p = None
    print(f"  No pude predecir el caso nuevo ({type(e).__name__}: {e}).")
    print("  Revise que FACTURA_NUEVA tenga las mismas columnas del CSV.")
print()
print("  Así se ve la IA metida DENTRO del proceso: no un informe, una decisión que")
print("  se toma sola todos los días, antes de que la factura se venza.")

# --- la regla del pipeline y la prueba del borrado ------------------------
sub("La regla del pipeline · y la prueba del borrado")
print("  El pipeline completo, que es lo que hay que saber defender ante un jurado:")
print()
print("     1. DATOS         4.000 facturas históricas ya respondidas")
print("     2. PREPARACIÓN   setup()          limpia, imputa, codifica y parte")
print("     3. ENTRENAMIENTO compare_models() nueve modelos compiten con evidencia")
print("     4. EVALUACIÓN    predict_model()  el examen que nadie vio")
print("     5. RESULTADO     modelo_cartera.pkl -> la lista de cobranza del lunes")
print()
print("  LA PRUEBA DEL BORRADO: quítele la IA a este proceso. ¿Funciona igual?")
print("  No. Sin el modelo, cobranza llama por monto o por orden alfabético y")
print("  la priorización se pierde. La IA no es un adorno en el informe: es el")
print("  paso que decide a quién se llama primero. Si al quitar la IA su proceso")
print("  funciona igual, la IA era decoración — y el jurado lo va a ver.")

# ===========================================================================
# LA GRÁFICA
# ===========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), facecolor=CREMA)
fig.suptitle(f"Cartera · ¿esta factura se paga tarde?   AutoML PyCaret · "
             f"campeón: {campeon_nombre}   Accuracy {acc:.2f} · F1 {f1v:.2f}",
             fontsize=12.5, color=NAVY, y=0.97)

ax1.set_facecolor("white")
ax1.imshow(cm, cmap="Blues", vmin=0)
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
if orden is not None and imp is not None:
    top = list(orden[::-1])
    ax2.barh([str(nombres[i])[:30] for i in top], [imp[i] for i in top], color=ORO,
             edgecolor=NAVY, linewidth=0.6)
    ax2.set_title(f"Qué mira el modelo ({etiqueta})", fontsize=11, color=NAVY, pad=10)
    ax2.grid(axis="x", color="#DDD8CC", linewidth=0.7)
else:
    nom = [str(r["Model"])[:26] for _, r in podio.iloc[:8].iterrows()][::-1]
    val = [float(r.get(METRICA_ORDEN, 0)) for _, r in podio.iloc[:8].iterrows()][::-1]
    ax2.barh(nom, val, color=ORO, edgecolor=NAVY, linewidth=0.6)
    ax2.set_title(f"El podio del AutoML ({METRICA_ORDEN}, validación cruzada)",
                  fontsize=11, color=NAVY, pad=10)
    ax2.grid(axis="x", color="#DDD8CC", linewidth=0.7)
ax2.tick_params(labelsize=9)
ax2.set_axisbelow(True)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.text(0.5, 0.015,
         "Datos sintéticos con semilla fija · AutoML con PyCaret · "
         "Diplomado en Inteligencia Artificial · UNAC · Clase 05",
         ha="center", fontsize=8.5, color="#7A8797")
fig.tight_layout(rect=(0, 0.035, 1, 0.93))
salida = os.path.join(AQUI, ARCHIVO_GRAFICA)
fig.savefig(salida, dpi=130, facecolor=CREMA)
plt.close(fig)

# Por si acaso: si alguna version de PyCaret alcanzo a dejar un logs.log en la
# carpeta de la plantilla, se borra. (Normalmente no llega aqui porque el
# archivo se queda en la carpeta temporal; ver el os.chdir del PASO 0.)
try:
    _b = os.path.join(AQUI, "logs.log")
    if os.path.exists(_b):
        os.remove(_b)
except OSError:
    pass

total = time.perf_counter() - t_inicio
titulo("LISTO")
print(f"  Gráfica guardada en : {salida}")
print(f"  Modelo guardado en  : {pkl}")
print(f"  Preparación (setup) : {seg_setup:.1f} s")
print(f"  Entrenamiento AutoML: {seg_entrenar:.1f} s")
print(f"  Tiempo total        : {total:.1f} segundos")
print()
print("  PARA USAR SUS DATOS:")
print("   1. Ponga su CSV en esta misma carpeta.")
print("   2. En el PANEL DE CONTROL cambie ARCHIVO_CSV y COLUMNA_OBJETIVO.")
print("   3. Meta en COLUMNAS_A_IGNORAR los identificadores y todo lo que solo se")
print("      sepa DESPUÉS de conocer la respuesta (eso es fuga de datos).")
print("   4. Vuelva a correr. El resto del pipeline no cambia. Eso es lo bonito.")
print()
print("  Regla de la casa: los datos de su empresa se quedan en su computador.")
print("=" * 78)
print()
