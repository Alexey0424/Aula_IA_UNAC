# Tres plantillas de Machine Learning, en su propio computador

**Diplomado en Inteligencia Artificial · UNAC · Clase 05**

En la Clase 04 se explicaron los tipos de Machine Learning y las métricas.
En el taller de Colab se pusieron 15 modelos a competir en la nube.
Esto es el paso siguiente: **el modelo corriendo en su máquina, sin internet,
sin cuenta de Google, sin que sus datos salgan a ningún lado.**

Son tres plantillas. Cada una responde una pregunta de gerente en una frase:

| | Plantilla | La pregunta, en una frase | Qué usa |
|---|---|---|---|
| 1 | **Supervisado** | *"¿Este cliente se va a atrasar en el pago?"* | Random Forest, Logistic Regression, Decision Tree |
| 2 | **No supervisado** | *"Agrúpeme mis productos en familias que yo no había visto."* | K-Means |
| 3 | **Deep Learning** | *"Clasifíqueme estas imágenes."* | Convolutional Neural Network (CNN) |

**Usted no escribe código.** Cada carpeta trae un archivo
`3_prompt_para_claude.txt` con el texto exacto que se copia y se pega en
Claude Code. Claude corre la plantilla y le explica el resultado.

---

## Lo primero: instalar

Todo está en **`0_instalar.txt`**, con las líneas exactas ya probadas. El
resumen:

```
py -m pip install scikit-learn pandas matplotlib      <- LÍNEA 1, obligatoria
py -m pip install torch                               <- LÍNEA 2, solo para la CNN
```

| | Descarga | Tiempo | Disco | Para qué |
|---|---|---|---|---|
| **Línea 1** | 84 MB | 47–53 s | 395 MB | Plantillas 1 y 2 |
| **Línea 2** | 127 MB | ~53 s | +640 MB | Plantilla 3 (la CNN) |

Los números son **medidos**, no estimados, en un Windows 10 con Python 3.12.

> **La línea 2 no se corre en clase.** Con 16 personas bajando 127 MB al mismo
> tiempo, el salón se queda sin internet. La plantilla 3 es tarea para la casa.

---

## Cómo se usa, en cuatro pasos

1. Abra **PowerShell** en la carpeta `3_Plantillas_ML_Local`
   (en el explorador de Windows: clic derecho sobre la carpeta →
   *Abrir en Terminal*).
2. Escriba `claude` y Enter.
3. Abra el archivo `3_prompt_para_claude.txt` de la plantilla que quiera,
   **copie el PROMPT 1 completo** y péguelo en Claude.
4. Cuando Claude le pida permiso para ejecutar el script, dígale que sí.

Cada plantilla imprime el resultado en español, explicado, y **guarda una
gráfica PNG** que se abre con doble clic.

---

## Plantilla 1 · Machine Learning supervisado

**Carpeta:** `1_supervisado`
**Pregunta:** ¿esta factura se va a pagar tarde?

Una cartera de 4.000 facturas de una distribuidora que le vende a cadenas,
mayoristas, tiendas de barrio e instituciones. De cada factura ya se sabe si se
pagó a tiempo o si se atrasó — por eso es **supervisado**: los ejemplos vienen
respondidos.

Tres modelos compiten con el mismo examen (la escalera de la Clase 04, en
versión de bolsillo):

- **Logistic Regression** — la línea recta, de 1958, y todavía manda en los bancos
- **Decision Tree** — preguntas en cascada; se puede leer y auditar
- **Random Forest** — 300 árboles votando

Qué imprime, además del podio:

- **Accuracy, Precision, Recall y F1 Score** traducidos a facturas y a llamadas
  de cobranza.
- La **matriz de confusión** casilla por casilla, con los dos errores separados:
  *«se le escapó»* (plata quieta) y *«falsa alarma»* (una llamada de más).
- El **control de overfitting**: acierto en estudio contra acierto en examen.
- La **tabla de umbrales** — la perilla del gerente. El mismo modelo alerta 188
  facturas con umbral 0.50 y 581 con umbral 0.20. *Cuántas llamadas de cobranza
  puedo pagar al mes* no es una pregunta técnica.
- Una **factura nueva** clasificada en vivo, para ver la IA metida dentro del
  proceso y no en un informe.

**Tiempo de la corrida: menos de 1 segundo.**

A quién le sirve directo: Ingrith (cartera y pagos de la clínica),
Santiago (cuentas de cadenas en Distintores), John Sebastián (certificación de
pagos en la Alcaldía), el equipo de Supermo.

---

## Plantilla 2 · Machine Learning no supervisado

**Carpeta:** `2_no_supervisado`
**Pregunta:** ¿qué familias hay en mi surtido que yo no había visto?

600 referencias de un supermercado con su comportamiento comercial: rotación,
margen, cuánto vende en promoción, devoluciones, quiebres de stock. **Nadie
etiquetó nada. No hay columna de respuesta.** El modelo propone los grupos.

Qué imprime:

- El **método del codo (Elbow)** y el **Silhouette Score** para cada `k` de 2 a 8.
- La **ficha de cada grupo** con promedios y un nombre comercial propuesto:
  *Locomotora de tráfico · Joya de margen · Adicto a la promoción · Cola larga
  dormida* — con qué haría un comprador con cada uno el lunes.
- La **verificación**: como los datos son sintéticos, sabemos qué familias se
  sembraron. K-Means las redescubrió solo, con **92,8 % de coincidencia**.
- La **lección incómoda**, que es lo más valioso de esta plantilla: el
  Silhouette Score dio 0,34 (una nota mediocre) y sin embargo la recuperación
  real fue del 93 %. La métrica midió geometría; el negocio vive en las
  fronteras. Quien hubiera botado ese modelo por su métrica habría botado un
  modelo que acierta 9 de cada 10.
- Un CSV `surtido_con_grupo.csv` para abrir en Excel y filtrar.

**Tiempo de la corrida: ~2 segundos.**

A quién le sirve directo: Diomer, Carlos Eduardo y Juan Esteban (categorías y
compras en Supermo), Abner (surtido de Vita Market), Gina (referencias del
taller de confección).

---

## Plantilla 3 · Deep Learning con red convolucional (CNN)

**Carpeta:** `3_deep_learning_cnn`
**Pregunta:** ¿esta lámina de vidrio pasa, o en qué falló?

> **Esta es la pesada.** Necesita la LÍNEA 2 (127 MB). Es **tarea para la casa**,
> no taller de clase.

2.400 imágenes simuladas de 28 × 28 píxeles de láminas de vidrio saliendo de la
línea de corte, en cuatro clases: **OK · Rayón · Burbuja · Astillado**.

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

Y el argumento gerencial completo, que también lo imprime:

> Con una tabla de Excel de 2.000 filas, el Random Forest le gana a la red —
> y es más barato y más explicable. Con imágenes, audio o texto, la red gana y
> no hay discusión. **No se deje vender redes neuronales para problemas de
> Excel.**

También imprime la **letra menuda**: ese 0,97 es sobre imágenes sintéticas,
limpias y parecidas entre sí. Con fotos de verdad —reflejos, polvo en el lente,
la luz del turno de la noche— el número baja, y baja harto.

**Tiempo de la corrida: 1,5 s de entrenamiento; 5 a 6 s el script completo**
(cargar PyTorch se demora más que entrenar la red).

A quién le sirve directo: Katerine (vidrio y aluminio en Coti Vidrios), y
cualquiera que tenga un problema de fotos: Ingrith leyendo facturas, Katerine
leyendo planos, Flor revisando documentos de proveedores.

---

## Los datos son sintéticos, y eso se dice siempre

Los tres conjuntos de datos los **inventa un script con semilla fija**. No son
datos de Supermo, ni de Distintores, ni de la clínica oftalmológica, ni de Coti
Vidrios, ni de ninguna entidad.

Se hacen así por tres razones:

1. **Corren sin internet.** En clase no se descarga ni un byte de datos.
2. **Son reproducibles.** Semilla fija: todo el salón obtiene los mismos números
   y se puede comparar.
3. **No exponen a nadie.** Ningún dato de ninguna empresa sale de ninguna parte.

Cada carpeta tiene su `1_generar_datos.py`. Si borra el CSV, el script de
entrenamiento lo vuelve a generar solo. Y si quiere ver de dónde salen los
datos, ábralo: la regla oculta que el modelo tiene que descubrir está escrita
ahí, con comentarios.

**Para el proyecto de grado:** si usa datos sintéticos en una entrega, dígalo.
Hacer pasar datos inventados por reales es una falta grave, y se nota.

---

## Lo que hay en cada carpeta

```
3_Plantillas_ML_Local/
├── LEEME.md                     este archivo
├── 0_instalar.txt               las líneas de instalación, probadas
├── 4_Informe_Verificacion.md    la salida real de cada corrida y los tiempos
├── 1_supervisado/
│   ├── 1_generar_datos.py       crea cartera_clientes.csv
│   ├── 2_entrenar.py            entrena, compara y explica
│   ├── 3_prompt_para_claude.txt el texto que se copia y se pega
│   ├── cartera_clientes.csv     4.000 facturas (se abre en Excel)
│   └── resultado_supervisado.png
├── 2_no_supervisado/
│   ├── 1_generar_datos.py       crea surtido_productos.csv
│   ├── 2_entrenar.py
│   ├── 3_prompt_para_claude.txt
│   ├── surtido_productos.csv    600 referencias
│   ├── surtido_con_grupo.csv    el mismo, con el grupo asignado
│   └── resultado_clusters.png
└── 3_deep_learning_cnn/
    ├── 1_generar_datos.py       crea imagenes_vidrio.npz
    ├── 2_entrenar.py
    ├── 3_prompt_para_claude.txt
    ├── imagenes_vidrio.npz      2.400 imágenes (6,3 MB)
    ├── muestras_vidrio.png      ÁBRALA: las 4 clases, para verlas
    └── resultado_cnn.png
```

En los tres scripts de entrenamiento hay un bloque marcado
**`PANEL DE CONTROL`** arriba. **Ahí y solo ahí se cambian cosas.** Todo lo
demás corre solo.

---

## Las dos reglas de la casa

1. **Sus datos se quedan en su computador.** Eso es la mitad del sentido de
   correr esto en local y no en la nube. Ningún script sube nada a ninguna
   parte, y los prompts para Claude lo dicen explícitamente.
2. **Nunca entrene con datos que no ha mirado.** Por eso la plantilla 3 genera
   `muestras_vidrio.png` antes de entrenar, y la plantilla 1 le muestra las
   primeras cinco filas. Ábralos.

---

## Si se atasca

La **regla de los diez minutos**: si lleva diez minutos peleando con lo mismo,
pare. Pegue el error completo en Claude Code con esta frase:

> Me salió este error corriendo las plantillas del diplomado. Estoy en Windows
> y no soy programador. Dime en pasos numerados qué hago, y no instales nada
> sin avisarme primero.

Y siga mirando la clase. Lo suyo se resuelve en asesoría.
