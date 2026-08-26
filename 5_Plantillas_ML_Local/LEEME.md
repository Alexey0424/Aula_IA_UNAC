# Tres plantillas de Machine Learning, en su propio computador

**Diplomado en Inteligencia Artificial · UNAC · Clase 05**

En la Clase 04 se explicaron los tipos de Machine Learning y las métricas.
En el taller de Colab se pusieron 15 modelos a competir en la nube.
Esto es el paso siguiente: **el modelo corriendo en su máquina, sin internet,
sin cuenta de Google, sin token, y sin que sus datos salgan a ningún lado.**

Son tres plantillas. Cada una responde una pregunta de gerente en una frase:

| | Plantilla | La pregunta, en una frase | Qué usa | Entrena con |
|---|---|---|---|---|
| 1 | **Supervised learning con PyCaret** | *"¿Esta factura se va a pagar tarde?"* | AutoML: nueve modelos compiten | datos tabulares |
| 2 | **Autoencoder** | *"De estos 3.000 pagos, ¿cuáles 30 miro yo primero?"* | red neuronal (PyTorch) | datos tabulares |
| 3 | **Convolutional Neural Network (CNN)** | *"¿Esta lámina de vidrio pasa, o en qué falló?"* | red convolucional (PyTorch) | imágenes |

**Usted no escribe código.** Cada carpeta trae un archivo
`3_prompt_para_claude.txt` con el texto exacto que se copia y se pega en
Claude Code. Claude corre la plantilla y le explica el resultado.

---

## ⬛ Lo primero, y lo único que no se puede saltar: son DOS instalaciones

Las tres plantillas **no pueden vivir en la misma instalación de Python.**

- La plantilla 1 usa **PyCaret**, que exige **numpy versión 1**.
- Las plantillas 2 y 3 usan **PyTorch**, que exige **numpy versión 2**.

`numpy` es la librería de cálculo que está por debajo de todo, y solo puede
haber **una** versión instalada a la vez. No es un problema de configuración:
es un techo.

**Esto lo probamos, no lo estamos suponiendo.** Si instala PyCaret y después
PyTorch en el mismo Python, PyTorch queda roto — y queda roto **en silencio**:
`pip` dice *"Successfully installed torch"* y no se queja. El error aparece
después, al correr la plantilla 3:

```
OSError: [WinError 1114] A dynamic link library (DLL) initialization
routine failed. Error loading "...\torch\lib\c10.dll"
```

Y si trata de arreglarlo subiendo numpy, entonces **se rompe PyCaret**:

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

Arregla una y rompe la otra.

### La solución: dos entornos separados que no se ven entre sí

```
C:\ia\env_pycaret     ->  Plantilla 1  (PyCaret / AutoML)
C:\ia\env_deep        ->  Plantillas 2 y 3  (PyTorch)
```

Se crean **una vez** y no se vuelven a tocar. Las líneas exactas están en
**`0_instalar.txt`**. El resumen:

```powershell
# PASO 1 - el de la clase
py -m venv C:\ia\env_pycaret
C:\ia\env_pycaret\Scripts\python.exe -m pip install pycaret-core matplotlib pandas numpy

# PASO 2 - tarea para la casa, NO en clase
py -m venv C:\ia\env_deep
C:\ia\env_deep\Scripts\python.exe -m pip install torch scikit-learn pandas matplotlib numpy
```

| | Disco | Tiempo | Paquetes | Para qué |
|---|---|---|---|---|
| **PASO 1** | 925 MB | 2–4 min | 102 | Plantilla 1 |
| **PASO 2** | 1.003 MB | 3–6 min | 31 | Plantillas 2 y 3 |

Los números son **medidos** en un Windows 10 con Python 3.12.10, el
26-ago-2026, creando los dos entornos desde cero.

> **El PASO 2 no se corre en clase.** Es más de 1 GB. Con 16 personas bajando
> eso al mismo tiempo, el salón se queda sin internet. Las plantillas 2 y 3
> son tarea para la casa.

> **Ojo con el nombre:** el paquete es **`pycaret-core`**, con guion y con
> *core*. El paquete de PyPI que se llama solo `pycaret` **no funciona con
> Python 3.12**. Verificado.

> **¿Por qué en `C:\ia` y no aquí mismo?** Windows no aguanta rutas de más de
> 260 caracteres y PyTorch tiene nombres de archivo larguísimos por dentro. En
> una carpeta profunda la instalación falla; en `C:\ia` funciona siempre.

---

## La regla de oro para correr las plantillas

**Cada plantilla se corre con su propio Python, escrito completo.
Nunca con `py` ni con `python` a secas.**

```powershell
# Plantilla 1
C:\ia\env_pycaret\Scripts\python.exe 2_entrenar.py

# Plantillas 2 y 3
C:\ia\env_deep\Scripts\python.exe 2_entrenar.py
```

Si se equivoca de entorno le sale `ModuleNotFoundError: No module named
'pycaret'` (o `'torch'`). **Los dos errores significan lo mismo: se equivocó
de Python.** No falta instalar nada — no instale nada, solo cambie la línea.

En la práctica usted casi nunca va a escribir esto: el
`3_prompt_para_claude.txt` de cada carpeta ya lleva la línea correcta.

---

## Cómo se usa, en cuatro pasos

1. Abra **PowerShell** en la carpeta `3_Plantillas_ML_Local`
   (en el explorador de Windows: clic derecho sobre la carpeta →
   *Abrir en Terminal*).
2. Escriba `claude` y Enter.
3. Abra el `3_prompt_para_claude.txt` de la plantilla que quiera,
   **copie el PROMPT 1 completo** y péguelo en Claude.
4. Cuando Claude le pida permiso para ejecutar el script, dígale que sí.

Cada plantilla imprime el resultado en español, explicado, y **guarda una
gráfica PNG** que se abre con doble clic.

---

## El pipeline: lo mismo en las tres

Las tres plantillas dicen el mismo cuento en cinco pasos. Aprenderse esos
cinco pasos es aprenderse la clase:

```
1. DATOS  ->  2. PREPARACIÓN  ->  3. ENTRENAMIENTO  ->  4. EVALUACIÓN  ->  5. RESULTADO
```

Y las tres terminan con la misma pregunta, que es la doctrina del curso:

> **La prueba del borrado:** quítele la IA al proceso. ¿Funciona igual?
> Si funciona igual, **la IA era decoración** — y el jurado lo va a ver.

---

## Plantilla 1 · Supervised learning con PyCaret (AutoML)

**Carpeta:** `1_supervisado` · **Entorno:** `env_pycaret` · **Corrida: ~10 s**
**Pregunta:** ¿esta factura se va a pagar tarde?

Una cartera de **4.000 facturas** de una distribuidora que le vende a cadenas,
mayoristas, tiendas de barrio e instituciones. De cada factura ya se sabe si se
pagó a tiempo o si se atrasó — por eso es **supervisado**: los ejemplos vienen
respondidos.

**Lo que hace especial a esta plantilla es que usted no escoge el modelo.**
Le entrega la tabla, le dice cuál columna es la respuesta, y PyCaret hace el
resto. Eso es **AutoML** (*Automated Machine Learning*).

**Nueve modelos compiten** con el mismo examen: Logistic Regression, Ridge
Classifier, Decision Tree, Random Forest, Extra Trees, Gradient Boosting,
AdaBoost, K Neighbors y Naive Bayes.

En la corrida de referencia ganó **Gradient Boosting Classifier** con
**Accuracy 0,815** y **F1 0,641** sobre el examen. Naive Bayes sacó **F1 0,000**
— y esa es una de las mejores preguntas de la clase: *¿cómo saca 0,68 de
Accuracy y 0,00 de F1 al mismo tiempo?*

Qué imprime, además del podio:

- **Lo que `setup()` hizo solo:** detectó qué columnas son números y cuáles
  texto, convirtió el texto a números (*one-hot encoding*), rellenó los vacíos,
  partió los datos y armó la validación cruzada. Nadie se lo pidió. **Eso es
  medio día de trabajo en una línea.**
- **La diferencia entre validación cruzada y examen**, que es donde se confunde
  todo el mundo: *se elige con validación cruzada, se reporta con el examen.*
- **Accuracy, Precision, Recall, F1 y AUC** traducidos a facturas y a llamadas
  de cobranza.
- La **matriz de confusión** casilla por casilla, con los dos errores separados
  y costeados: *«se le escapó»* (plata quieta) y *«falsa alarma»* (una llamada
  de más).
- El **control de overfitting**: validación cruzada contra examen.
- La **tabla de umbrales** — la perilla del gerente. El mismo modelo, sin
  reentrenar nada, alerta 196 facturas con umbral 0,50 y 151 con umbral 0,70.
  *Cuántas llamadas de cobranza puedo pagar al mes* no es una pregunta técnica.
- **`modelo_cartera.pkl`** (139 KB): el modelo entrenado, listo para que un
  sistema lo use todos los días. Ese archivo es el entregable.
- Una **factura nueva** clasificada en vivo (93,3 % de probabilidad de atraso →
  *llamar antes del vencimiento*).

A quién le sirve directo: Ingrith (cartera y pagos de la clínica),
Santiago (cuentas de cadenas en Distintores), John Sebastián (certificación de
pagos en la Alcaldía), el equipo de Supermo.

---

## Plantilla 2 · Autoencoder sobre datos (detección de anomalías)

**Carpeta:** `2_no_supervisado` · **Entorno:** `env_deep` · **Corrida: ~7 s**
**Pregunta:** de estos 3.000 pagos, ¿cuáles 30 debo mirar yo primero?

**3.000 movimientos de pago a proveedores** de una clínica: insumos médicos,
servicios, arrendamientos, papelería, mantenimiento. **Nadie marcó cuáles
estaban raros. No hay columna de respuesta.**

Una red neuronal aprende cómo se ve un pago **normal**, apretando cada pago a
solo **4 números** y volviéndolo a abrir. Lo que no logra reconstruir bien, lo
levanta como sospechoso. Ese es el **error de reconstrucción**, y es el puntaje
de sospecha.

> **La trampa del docente.** El CSV trae una columna `es_anomalia`. **En la vida
> real usted no la tiene** — si la tuviera, haría un clasificador supervisado,
> o sea la plantilla 1. Aquí existe solo para poder calificar al modelo al
> final. El script la saca **antes** de entrenar. Cuando ponga sus datos:
> `COLUMNA_VERIFICACION = None`.

Qué imprime:

- Por qué el modelo se entrena **solo con los movimientos normales** (si se
  entrena con todo, aprende que lo raro también es normal y deja de verlo).
- El error promedio de los normales (**0,146**) contra el de los raros
  (**0,283**): casi el doble. Ahí está toda la idea.
- **Recall 0,740 · Precision 0,730** con el umbral que quedó.
- La tabla **«qué patrón sí atrapó y cuál se le escapa»**, que es la más útil
  para el negocio: atrapa *sobrecosto con un solo aprobador* (Recall 0,97) y
  *monto redondo sin soportes* (0,89), pero se le va la mitad del
  *fraccionamiento* (0,58) y del *pago fuera de horario* (0,53). **Eso se
  reporta, no se esconde:** esos dos patrones se siguen revisando a mano.
- La **perilla del gerente**: con K = 0,0 levanta 463 pagos; con K = 3,0
  levanta 34 con Precision 1,000. *¿Cuántos pagos al mes puede revisar mi
  equipo?* define K.
- **La lista de trabajo:** de los 30 movimientos con más error, **30 estaban
  sembrados como raros (100 %)**. Al azar se habrían esperado 4. El modelo
  concentró **6,7 veces más hallazgos** en las mismas horas de auditoría.
- **`movimientos_revisados.csv`** para abrir en Excel, ya ordenado de más
  sospechoso a menos. **Ese archivo es el entregable. No el modelo: la lista.**

> **Lo que hay que tener claro:** este método levanta lo **atípico**, no lo
> **ilegal**. Un pago raro puede ser perfectamente legítimo. La salida es una
> lista de **revisión humana**, nunca una acusación.

A quién le sirve directo: Ingrith (única responsable del área contable de la
clínica), Flor (validación documental y listas de chequeo en el Área
Metropolitana), John Sebastián (almacenista municipal, certifica precios en la
Alcaldía), Sebastián Vélez (validación manual repetitiva en hospitales).

---

## Plantilla 3 · Convolutional Neural Network (CNN) sobre imágenes

**Carpeta:** `3_deep_learning_cnn` · **Entorno:** `env_deep` · **Corrida: ~6 s**
**Pregunta:** ¿esta lámina de vidrio pasa, o en qué falló?

> **Es la pesada.** Necesita el PASO 2 de la instalación (más de 1 GB).
> Es **tarea para la casa**, no taller de clase.

**2.400 imágenes** simuladas de 28 × 28 píxeles de láminas de vidrio saliendo
de la línea de corte, en cuatro clases: **OK · Rayón · Burbuja · Astillado**.

Lo que hace especial a esta plantilla: **corre dos modelos y los compara con el
mismo examen.**

| Modelo | Cómo mira la imagen | Accuracy medido |
|---|---|---|
| Logistic Regression | los 784 píxeles como columnas sueltas | **0,66** |
| CNN | vecindarios de píxeles (convolución) | **0,97** |

**31,5 puntos de diferencia.** Los dos vieron las mismas imágenes. Lo único que
cambió fue mirar vecindarios en vez de píxeles sueltos. Ahí está toda la
lección: un rayón movido tres píxeles a la derecha es, para el modelo clásico,
una fila de datos completamente distinta; para la convolución sigue siendo un
rayón.

También imprime el **Recall por clase**: caza el 100 % de las OK y el 99,2 % de
las astilladas, pero se le va el 7,5 % de los rayones (los confunde con
burbujas). Y el argumento gerencial completo:

> Con una tabla de Excel de 2.000 filas, el Gradient Boosting le gana a la red
> — y es más barato y más explicable. Con imágenes, audio o texto, la red gana
> y no hay discusión. **No se deje vender redes neuronales para problemas de
> Excel.**

Y la **letra menuda**, que se dice siempre: ese 0,97 es sobre imágenes
sintéticas, limpias y parecidas entre sí. Con fotos de verdad —reflejos, polvo
en el lente, la luz del turno de la noche— el número baja, y baja harto.

A quién le sirve directo: Katerine (líder de ingeniería de vidrio y aluminio en
Coti Vidrios — es literalmente su producto), y cualquiera con un problema de
fotos: Ingrith leyendo facturas, Katerine leyendo planos, Gina revisando
terminados en el taller de confección.

---

## Los datos son sintéticos, y eso se dice siempre

Los tres conjuntos de datos los **inventa un script con semilla fija**. No son
datos de Supermo, ni de Distintores, ni de la clínica oftalmológica, ni de Coti
Vidrios, ni de ninguna entidad.

Se hacen así por tres razones:

1. **Corren sin internet.** En clase no se descarga ni un byte de datos.
2. **Son reproducibles.** Semilla fija: todo el salón obtiene los mismos
   números y se puede comparar.
3. **No exponen a nadie.** Ningún dato de ninguna empresa sale de ninguna parte.

Cada carpeta tiene su `1_generar_datos.py`. Si borra el CSV, el script de
entrenamiento lo vuelve a generar solo. Y si quiere ver de dónde salen los
datos, ábralo: **la regla oculta que el modelo tiene que descubrir está escrita
ahí**, con comentarios.

**Para el proyecto de grado:** si usa datos sintéticos en una entrega, dígalo.
Hacer pasar datos inventados por reales es una falta grave, y se nota.

---

## Lo que hay en cada carpeta

```
5_Plantillas_ML_Local/
├── LEEME.md                       este archivo
├── 0_instalar.txt                 los dos entornos, con las líneas probadas
├── 1_supervisado/
│   ├── 1_generar_datos.py         crea cartera_clientes.csv
│   ├── 2_entrenar.py              AutoML con PyCaret: 9 modelos compiten
│   ├── 3_prompt_para_claude.txt   el texto que se copia y se pega
│   ├── cartera_clientes.csv       4.000 facturas (se abre en Excel)
│   └── resultado_supervisado.png  cómo se ve el resultado esperado
├── 2_no_supervisado/
│   ├── 1_generar_datos.py         crea movimientos_contables.csv
│   ├── 2_entrenar.py              autoencoder en PyTorch
│   ├── 3_prompt_para_claude.txt
│   ├── movimientos_contables.csv  3.000 pagos
│   ├── movimientos_revisados.csv  la lista de trabajo, ya ordenada
│   └── resultado_autoencoder.png
└── 3_deep_learning_cnn/
    ├── 1_generar_datos.py         crea imagenes_vidrio.npz
    ├── 2_entrenar.py              CNN vs. modelo clásico, mismo examen
    ├── 3_prompt_para_claude.txt
    ├── muestras_vidrio.png        ÁBRALA: las 4 clases, para verlas
    └── resultado_cnn.png
```

Los CSV que vienen incluidos son **el resultado esperado**, para que usted
compare. Lo que **no** viaja en este repositorio, porque pesa y porque el
script lo regenera solo en la primera corrida: las gráficas `.png`,
`imagenes_vidrio.npz` (6,6 MB) y `modelo_cartera.pkl`. Si no están, no falta
nada: corra la plantilla y aparecen en su computador.

En los tres `2_entrenar.py` hay un bloque marcado **`PANEL DE CONTROL`** arriba.
**Ahí y solo ahí se cambian cosas.** Todo lo demás corre solo.

---

## Para Claude (y para cualquier agente de IA)

Cada `3_prompt_para_claude.txt` termina con un **CONTRATO TÉCNICO**: qué
intérprete usar, qué columnas y tipos espera la plantilla, qué se puede cambiar,
**qué no se debe tocar**, cómo validar los datos del estudiante antes de
entrenar, y qué significan los errores comunes.

Si le va a pedir a Claude que adapte una plantilla a sus datos reales, **use el
PROMPT 3** de esa carpeta: ya trae la revisión previa completa, incluida la
cacería de **fuga de datos** (*data leakage*), que es el error número uno.

---

## Las dos reglas de la casa

1. **Sus datos se quedan en su computador.** Eso es la mitad del sentido de
   correr esto en local y no en la nube. Ningún script sube nada a ninguna
   parte, y los prompts para Claude lo dicen explícitamente.
2. **Nunca entrene con datos que no ha mirado.** Por eso la plantilla 3 genera
   `muestras_vidrio.png` antes de entrenar, y las plantillas 1 y 2 le muestran
   las primeras cinco filas. Ábralos.

---

## Si se atasca

La **regla de los diez minutos**: si lleva diez minutos peleando con lo mismo,
pare. Pegue el error completo en Claude Code con esta frase:

> Me salió este error corriendo las plantillas del diplomado. Estoy en Windows,
> no soy programador, y las plantillas usan dos entornos virtuales separados
> (`C:\ia\env_pycaret` para PyCaret y `C:\ia\env_deep` para PyTorch) porque no
> pueden convivir. Dime en pasos numerados qué hago, y no instales ni
> actualices nada sin avisarme primero.

Y siga mirando la clase. Lo suyo se resuelve en asesoría.

**Y si algo se rompió del todo:** no lo repare, bórrelo y vuélvalo a crear.
`Remove-Item -Recurse -Force C:\ia\env_pycaret` y repita el PASO 1. Borrar un
entorno virtual no le hace nada a su computador ni a su Python: es una carpeta
y nada más.
