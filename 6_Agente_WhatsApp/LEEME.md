# Agente de WhatsApp sobre el informe · kit de la Clase 12

Conecta **el informe que usted ya publicó en Cloudflare** (Clase 07) a **su WhatsApp**: le
pregunta por texto o nota de voz y le contesta con lo que dice su informe; le pide el informe y le
llega en PDF. Opcional: una agenda de citas con recordatorios.

**Usted no escribe comandos.** Le pega este prompt a Claude Code y él sigue la skill
`/agente-whatsapp`:

```
Actualiza el aula y conecta mi informe a mi WhatsApp siguiendo la skill /agente-whatsapp
(carpeta 6_Agente_WhatsApp). Mi informe está publicado en: <la dirección de su informe>
```

Usted solo hace dos cosas: **autorizar Cloudflare** en el navegador si se lo pide y **escanear el
QR** con el celular.

---

## Cómo funciona: arquitectura semihíbrida

```
su celular ──► su PC: PUENTE ──────────► su Cloudflare: CEREBRO ──────► su INFORME publicado
 WhatsApp      (dispositivo vinculado,    (Worker + Workers AI:          (lo abre en un navegador
               como WhatsApp Web)          Whisper + LLM con tools)        de Cloudflare: texto y PDF)
           ◄──                        ◄──  respuesta, o el PDF
```

| Pieza | Dónde vive | Carpeta | ¿Igual para todos? |
|---|---|---|---|
| **Puente** | Su computador | `1_Puente/` | Sí. Solo cambia `config.json` |
| **Cerebro** | Su cuenta de Cloudflare | `2_Cerebro/` | Sí. Solo cambia `wrangler.toml` |
| **Informe** | Su cuenta de Cloudflare (Clase 07) | — | Es el suyo. No se toca |

- **Por qué semihíbrida:** la conexión con WhatsApp tiene que quedarse abierta todo el tiempo y un
  Worker solo vive lo que dura una petición. Por eso la puerta vive en el PC y el cerebro en la nube.
  El puente **llama hacia afuera**: no se abren puertos ni se monta túnel.
- **Por qué no la API oficial de Meta:** exige verificar un negocio (días) y desde el
  1-oct-2026 cobra cada respuesta. Para clientes reales de una empresa, esa sigue siendo la vía.

## El puente (`1_Puente/`)

Entra a WhatsApp con la librería **Baileys** como *dispositivo vinculado*, igual que WhatsApp Web:
se escanea un QR una vez y la sesión queda guardada en `sesion_whatsapp/`.

- **Un solo ícono, «WhatsApp IA»,** en el escritorio: un clic prende el puente y abre el panel
  (`http://localhost:3939`); si ya estaba prendido, solo abre el panel. Lo crea `crear_accesos.ps1`.
- **Arranca solo con Windows** (minimizado, sin abrir el navegador) y en el **último modo** en que
  se dejó. Si al arrancar hace falta el QR, el panel se abre solo.
- **El interruptor** (en el panel, o escribiéndose a sí mismo en WhatsApp):

  | Modo | A quién le contesta | Orden por WhatsApp |
  |---|---|---|
  | 🔴 Apagado | A nadie. Sigue vinculado | `bot off` |
  | 🟢 **Solo yo** | Solo el chat consigo mismo («Mensaje para mí») | `bot yo` |
  | 🟠 Abierto | Cualquier chat individual. **Se apaga solo** a los 15 min | `bot abierto` · `bot abierto 5` |

  Nunca contesta grupos, estados ni canales. `bot estado` dice en qué modo está.
- **Notas de voz:** las baja y se las pasa al cerebro. **Documentos:** si el cerebro devuelve el
  PDF, lo manda como documento de WhatsApp.
- **Memoria corta:** el puente guarda los últimos mensajes de cada chat (30 min) y se los devuelve
  al cerebro, para que «a las 3» se entienda después de «¿a qué hora?».

| Archivo | Para qué |
|---|---|
| `puente.mjs` | Todo el puente: WhatsApp, interruptor, documentos, recordatorios y el panel |
| `pagina.html` | El panel de `http://localhost:3939` |
| `config.ejemplo.json` | Plantilla de `config.json`: dirección del cerebro, clave, nivel 2 |
| `1_INICIAR_PUENTE.bat` · `2_DETENER_PUENTE.bat` | Prender y apagar (el ícono usa el primero) |
| `3_CREAR_ICONO_Y_ARRANQUE.bat` · `4_QUITAR_ICONO_Y_ARRANQUE.bat` · `crear_accesos.ps1` | El ícono y el arranque con Windows |
| `iconos/whatsapp_ia.ico` | El ícono |
| `package.json` · `package-lock.json` | Baileys 7.0.0-rc14, qrcode, pino (versiones fijas) |

## El cerebro (`2_Cerebro/`)

Un Worker de Cloudflare. Por cada mensaje:

1. Si es nota de voz, **Whisper** (`@cf/openai/whisper-large-v3-turbo`) la vuelve texto.
2. **Lee el informe** abriéndolo en un navegador de Cloudflare (*Browser Rendering*): lo que se ve,
   el texto de las pestañas o filtros ocultos y los datos que trae el código de la página (los de las
   gráficas). Lo guarda 15 minutos. En la misma visita saca el **PDF** (horizontal, tal como se ve).
3. Un **LLM** (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) recibe el mensaje, el contenido del
   informe y la lista de **tools**, y contesta o pide una tool. **El modelo escoge; el código ejecuta.**

| Nivel | Tools | Qué necesita |
|---|---|---|
| **1 · todos** | Contestar con el informe · `enviar_informe_pdf` | AI, navegador, KV |
| **2 · opcional** | `agendar_cita` · `ver_agenda` · `cancelar_cita` · `guardar_nota` · `ficha_cliente` · recordatorio 30 min antes | Además, una base **D1** |

| Archivo | Para qué |
|---|---|
| `worker.js` | Todo el cerebro. **No se modifica**: es igual para todos |
| `wrangler.ejemplo.toml` | Plantilla de `wrangler.toml`: nombre, `INFORME_URL`, `EMPRESA`, `CONTEXTO_EXTRA`, ids |
| `package.json` | `@cloudflare/puppeteer` 1.4.0 (el navegador de Cloudflare) |
| `esquema_agenda.sql` | Las tablas de la agenda (nivel 2) |

Direcciones del cerebro: `POST /api/mensaje` (la usa el puente, exige la cabecera `x-clave`) ·
`GET /informe.pdf` · `GET /api/releer` (con clave: vuelve a leer el informe ya) ·
`GET /api/recordatorios` (con clave) · `GET /api/agenda` (nivel 2, pública) · `GET /api/estado`.

## La agenda en el informe (`3_Agenda_en_el_Informe/`, nivel 2, opcional)

`agenda_widget.html` es un bloque que se pega en el HTML del informe: muestra las próximas citas y
se actualiza solo cada 30 s. **Si el informe es público, la agenda también.** Con clientes reales,
mejor no pintarla y consultarla solo por WhatsApp.

## Lo que el agente aprendió a no hacer (medido el 15-oct-2026)

Sirve para la sustentación: **a un agente no se le cree, se le prueba.** Cada falla quedó atajada
en el código, no en las instrucciones, porque las instrucciones solas no bastaron.

1. **Mandaba el PDF para todo.** Con una sola tool a la mano, a «¿cuál fue el mejor mes?» le
   respondía con el PDF. Ahora la tool del PDF solo se le ofrece si la persona pidió el informe.
2. **Escribía la llamada en vez de hacerla.** Contestaba con el texto `{"type":"function"…}`, que le
   habría llegado así al usuario. Ahora ese texto se lee como llamada y nunca se manda.
3. **Se equivocaba de día.** «El martes» lo agendó el lunes. Ahora si la persona dice hoy, mañana o
   un día de la semana, la fecha la calcula el código.
4. **Olvidaba con quién era la cita** después de «¿a qué hora?», y una vez puso de cliente a la
   empresa del informe. Ahora lo que ya se sabía de la cita a medias se completa en el código, y la
   memoria corta la guarda el puente: en Cloudflare KV tardaba hasta un minuto en verse.
5. **Cambiaba los nombres** («Julian», «Julién» por «Julián»). Ahora se usa el nombre tal como lo
   escribió la persona.
6. **Se negaba a interpretar** («Eso no aparece en el informe» ante «¿qué es lo más preocupante?»).
   Ahora distingue: un **dato** que no está, no lo inventa; una **lectura**, la hace con las cifras.

Del agente del docente vienen tres más: inventaba la hora si no se la decían (ahora pregunta),
fingía haber guardado algo sin llamar la tool (ahora se le vuelve a preguntar sin historial) y hacía
solo la mitad de un pedido doble (ahora revisa si quedó algo pendiente).

## Límites

- **El computador tiene que estar prendido** y sin suspenderse. Al volver, se reconecta solo.
- **Workers AI gratis: 10.000 neurons al día** por cuenta `[V]` (developers.cloudflare.com/workers-ai/platform/pricing),
  se recargan a las 00:00 UTC = 7:00 p. m. de Colombia. El LLM cobra 26.668 neurons por millón de
  tokens de entrada y 204.805 por millón de salida `[V]`, y en cada mensaje lee el informe completo
  (hasta 18.000 caracteres): del orden de 150 a 300 neurons por pregunta `[SV, estimado]`.
- **Navegador de Cloudflare gratis:** 10 minutos al día, un navegador nuevo cada 20 s `[V]`
  (developers.cloudflare.com/browser-rendering/limits).
- **Lo que una gráfica pinta sin el número escrito no se puede leer.** Sí se leen las tarjetas,
  las tablas y los datos que trae el código.
- **WhatsApp:** usarlo con un cliente no oficial va contra sus términos de servicio y puede terminar
  en bloqueo del número `[V]` (whatsapp.com/legal/terms-of-service). Es un ejercicio de clase, en
  modo «Solo yo».

## Cuidado

- **`sesion_whatsapp/` es la llave de su WhatsApp.** Quien copie esa carpeta, entra. No se comparte,
  no se sube a GitHub. `config.json` tiene la clave del cerebro.
- Su copia de trabajo vive en `mis_entregas/agente_whatsapp/`, que el aula nunca sube.
