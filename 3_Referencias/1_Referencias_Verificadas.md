# Referencias verificadas del curso

> Cada entrada fue verificada contra su fuente el **19 de agosto de 2026**. Los nombres de
> modelos y los precios de la IA cambian cada pocas semanas: antes de citar en el documento
> final, vuelva a abrir la fuente. Referencia que no se abrió, no se cita.

## El paper que lo empezó todo (promesa de la Clase 01 — cumplida)

- **Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł.,
  & Polosukhin, I. (2017). *Attention is all you need*.** arXiv:1706.03762.
  https://arxiv.org/abs/1706.03762 — el Transformer: la arquitectura detrás de Claude,
  ChatGPT, Gemini y Whisper. Dato curioso verificado: se inventó para traducción automática;
  el chatbot fue un efecto secundario.

## Modelos de Hugging Face vistos en la Clase 04 (con su licencia)

| Tarea | Modelo (repo exacto) | Licencia | ¿Uso comercial? |
|---|---|---|---|
| Voz → texto | `openai/whisper-large-v3-turbo` | MIT | ✅ Sí |
| Voz → texto (2026) | `Qwen/Qwen3-ASR-1.7B` | Apache-2.0 | ✅ Sí |
| Texto → voz (español) | `hexgrad/Kokoro-82M` (voces `ef_dora`, `em_alex`) | Apache-2.0 | ✅ Sí |
| Texto → voz (español) | `facebook/mms-tts-spa` | CC-BY-NC 4.0 | ❌ **No** |
| Texto → imagen | `Tongyi-MAI/Z-Image-Turbo` | Apache-2.0 | ✅ Sí |
| Texto → imagen | `black-forest-labs/FLUX.1-schnell` · `FLUX.2-klein-4B` | Apache-2.0 | ✅ Sí |
| Texto → imagen | `black-forest-labs/FLUX.2-dev` · `FLUX.1-dev` | FLUX Non-Commercial | ❌ **No** |
| Imagen → texto (visión/OCR) | `Qwen/Qwen3-VL-4B-Instruct` · `zai-org/GLM-OCR` | Apache-2.0 · MIT | ✅ Sí |
| Traducción | `google/madlad400-3b-mt` (419 idiomas) | Apache-2.0 | ✅ Sí |
| Traducción | `facebook/nllb-200-distilled-600M` | CC-BY-NC 4.0 | ❌ **No** («no liberado para producción», textual de su ficha) |
| Clasificación sin entrenar (100 idiomas) | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | MIT | ✅ Sí |
| Sentimiento en español | `pysentimiento/robertuito-sentiment-analysis` | Sin licencia declarada | ⚠️ Solo aprendizaje |

**La lección gerencial:** «abierto» no significa ni gratis de operar ni usable comercialmente.
Antes de montar un modelo en un proceso de su empresa, revise tres cosas distintas:
la **licencia** del modelo, el **costo de cómputo** para operarlo, y **quién ve sus datos**.

- Catálogo por tarea: https://huggingface.co/tasks
- Demos sin código (Spaces): https://huggingface.co/spaces — cuota gratis: ~5 min de GPU/día.
- API (Inference Providers): https://huggingface.co/docs/inference-providers — crédito gratis
  ~0,10 USD/mes; el error HTTP 402 significa que se agotó, no que usted hizo algo mal.

## Herramientas de los laboratorios

- **Prophet** (Meta) — pronóstico de series de tiempo. Viene preinstalado en Google Colab.
  Guía: https://facebook.github.io/prophet/docs/quick_start.html — está en «modo
  mantenimiento» desde la 1.4.0: API congelada y estable, **no** abandonado (6 versiones en
  los últimos 15 meses). El intervalo por defecto es del **80 %**.
- **PyCaret** — el laboratorio de experimentos. En Colab se instala con
  `pip install pycaret-core` (fork comunitario de sktime, 3.5.0, ago-2026; misma API).
  **Nunca** `pip install pycaret` (la 3.3.2 no funciona con el Python 3.12 de Colab).
  Repo del fork: https://github.com/sktime/pycaret
- **scikit-learn** — la caja de herramientas de ML clásico; preinstalada en Colab.
  https://scikit-learn.org
- **Google Colab** — el computador prestado: https://colab.research.google.com — secretos
  (icono 🔑) para guardar `HF_TOKEN`; el plan gratis restringe la GPU: los laboratorios del
  curso corren en CPU a propósito.
- **statsforecast** (Nixtla) — pronóstico en producción: https://github.com/Nixtla/statsforecast
- **Chronos-2** (Amazon) — pronóstico sin entrenar (foundation model, Apache-2.0):
  https://huggingface.co/amazon/chronos-2
- **Pronóstico sin código en Google Sheets** (TimesFM, feb-2026, requiere BigQuery):
  https://workspaceupdates.googleblog.com/2026/02/forecast-data-in-connected-sheets-BigQueryML-TimesFM.html

## Claude y el aula conectada

- Claude Code — memoria y CLAUDE.md (por qué el aula funciona):
  https://code.claude.com/docs/en/memory
- Claude Code — skills: https://code.claude.com/docs/en/skills
- App de escritorio (pestaña Code, sin terminal): https://code.claude.com/docs/en/desktop-quickstart
- GitMCP (plan B del aula): https://github.com/idosal/git-mcp

## Marco normativo colombiano (para el capítulo de datos del documento)

- **Ley 1581 de 2012** — régimen general de protección de datos personales en Colombia.
  Aplica al tratamiento de datos con IA. ⚠️ Verificar artículos puntuales contra la fuente
  primaria (SIC) antes de citarlos: www.sic.gov.co
- Política Nacional de IA — **CONPES 4144 (2025)**. ⚠️ Citar solo tras leer el texto oficial:
  https://colaboracion.dnp.gov.co/CDT/Conpes/Económicos/4144.pdf

## Lecturas recomendadas (pronóstico para gerentes)

- Hyndman, R. J., & Athanasopoulos, G. *Forecasting: Principles and Practice* (3.ª ed.,
  gratuita): https://otexts.com/fpp3/ — tendencia, estacionalidad, ciclo y errores de
  pronóstico, explicados con gráficas.
- Makridakis, S., et al. — competencia **M5**: los modelos complejos ganaron por ~14 %, pero
  las líneas base simples siguen siendo obligatorias.
  https://www.sciencedirect.com/science/article/pii/S0169207021001874
