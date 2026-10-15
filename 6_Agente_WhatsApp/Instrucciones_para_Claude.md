# Instrucciones para Claude · Agente de WhatsApp sobre el informe

**Diplomado en Inteligencia Artificial · UNAC · Clase 12 · Mg. Alexey David Velásquez Betancurt**

> **Para Claude Code.** Este archivo es todo lo que necesita para conectar el informe del estudiante
> a su WhatsApp. Sígualo de arriba abajo. El estudiante es un gerente que **no programa**: usted
> corre todos los comandos, le explica en español sencillo qué está pasando y le pide solo lo que
> está marcado como **«lo hace el estudiante»**.

---

## 0. Qué se va a construir

El estudiante ya tiene un **informe HTML publicado en Cloudflare** (lo hizo en la Clase 07, con
`npx wrangler deploy`, en una dirección como `https://informe-miempresa.suapellido.workers.dev`).
Al terminar, el estudiante se escribe a sí mismo en WhatsApp («Mensaje para mí»), le pregunta a su
informe por texto o nota de voz y le llega la respuesta; si pide el informe, le llega en PDF.

```
su celular ─► su PC: PUENTE (1_Puente) ─► su Cloudflare: CEREBRO (2_Cerebro) ─► su INFORME publicado
 WhatsApp     Baileys, dispositivo         Worker + Workers AI                    lo abre en un navegador
              vinculado (como WhatsApp      (Whisper + LLM con tools)             de Cloudflare: texto y PDF
              Web), llama hacia afuera
```

| Pieza | Dónde vive | ¿Se modifica? |
|---|---|---|
| **Puente** (`1_Puente/`) | Computador del estudiante | No. Solo se crea `config.json` |
| **Cerebro** (`2_Cerebro/`) | Cloudflare del estudiante | No. Solo se crea `wrangler.toml` |
| **Informe** | Cloudflare del estudiante | No (salvo el nivel 2 opcional, si lo pide) |

- **Nivel 1 (el de la clase):** preguntas sobre el informe + la tool `enviar_informe_pdf`.
- **Nivel 2 (opcional):** agenda en una base D1: `agendar_cita`, `ver_agenda`, `cancelar_cita`,
  `guardar_nota`, `ficha_cliente` y un recordatorio 30 minutos antes de cada cita.
- El cerebro **lee el informe abriéndolo en el navegador de Cloudflare** (Browser Rendering): lo
  visible, las pestañas o filtros ocultos y los datos que trae el código de la página. Por eso el
  mismo `worker.js` sirve para cualquier informe. El texto se guarda 15 min y el PDF 1 hora.
- **El modelo escoge, el código ejecuta:** el LLM decide si contesta o pide una tool; el Worker la corre.

## 1. Reglas que no se negocian

1. **El estudiante no escribe comandos.** Solo hace dos cosas: autorizar Cloudflare en el navegador
   (si hace falta) y **escanear el QR** con el celular.
2. **`sesion_whatsapp/` y `config.json` son llaves.** Quien copie `sesion_whatsapp/` entra al WhatsApp
   del estudiante. Nunca los muestre, no los copie a otro lado, no los suba a GitHub, no los pegue en el
   chat. La clave del puente **no se imprime** en pantalla. Nunca imprima tokens de Cloudflare.
3. **Modo de clase: «Solo yo»** (el bot solo contesta en el chat del estudiante consigo mismo). No active
   el modo Abierto ni `numeros_permitidos` si el estudiante no lo pide y entiende el riesgo.
4. **Antes de empezar, dígale el riesgo en dos líneas** y espere a que diga que sigue: el puente es un
   cliente **no oficial** de WhatsApp; usarlo va contra los términos de servicio de WhatsApp y puede
   terminar en bloqueo del número. Es un ejercicio de clase en modo «Solo yo». Si tiene un segundo
   número, mejor.
5. **Si el estudiante tiene la carpeta del aula** (`Aula_IA_UNAC`, con `CLAUDE.md` y `6_Agente_WhatsApp/`),
   nada suyo se escribe dentro de `6_Agente_WhatsApp/`: es material del curso y se rompería el `git pull`.
6. **Pruebe con Node, no con curl,** cuando mande texto con tildes o ñ: desde Git Bash en Windows curl
   daña la codificación y las pruebas dan resultados falsos. Abajo está el script de prueba.
7. **No cambie `worker.js` ni `puente.mjs`.** Si algo no funciona, revise la configuración y la tabla de
   problemas. Son iguales para todo el salón y ya traen atajadas las fallas que se midieron.

## 2. Verificar antes de tocar nada

1. **Sistema operativo** (Windows o Mac).
2. **Node.js 20 o más:** `node --version`. Si falta:
   - Windows: `winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements`.
     Después use la ruta completa `"C:\Program Files\nodejs\node.exe"` / `npm.cmd` / `npx.cmd`, o abra otra terminal.
   - Mac: `brew install node`, o el instalador de nodejs.org.
3. **La dirección del informe.** Viene en el prompt; si no, pídasela. Haga un GET y confirme que responde
   200 y que el `<title>` es el de su informe. Si responde 404 o pide clave, el informe no es público:
   dígaselo y deténgase.
4. **Cloudflare.** `npx wrangler whoami`.
   - Si el estudiante tiene el `.env` de la Clase 07 con `CLOUDFLARE_API_TOKEN` (y `CLOUDFLARE_ACCOUNT_ID`),
     cárguelo como variable de entorno **sin imprimirlo**.
   - Si no hay sesión, o si más adelante sale `Authentication error [code: 10000]` al crear el KV o la D1
     (el token de la Clase 07 puede no tener esos permisos): quite `CLOUDFLARE_API_TOKEN` del entorno y
     corra `npx wrangler login`. **Lo hace el estudiante:** en el navegador que se abre, clic en **Allow**.
5. **Pregúntele, en un solo mensaje:**
   - el **nombre de la empresa** tal como quiere verlo en WhatsApp;
   - opcional, **una o dos frases de contexto** para leer bien sus números (qué es bueno y qué es malo,
     qué periodo cubre). Si en la Clase 08 llenó el CAMPO 5 del prompt, sirve tal cual;
   - si quiere solo el **nivel 1** o también el **nivel 2** (agenda);
   - si quiere que el puente **arranque solo al prender el computador**.

## 3. Conseguir el kit y hacer la copia de trabajo

El kit es la carpeta `6_Agente_WhatsApp/` (trae `1_Puente/`, `2_Cerebro/` y `3_Agenda_en_el_Informe/`).
Tómela del primer lugar donde exista:

1. **El aula del estudiante**, si la tiene clonada: primero `git pull --ff-only` dentro del aula, luego
   `<aula>/6_Agente_WhatsApp/`.
2. **La carpeta que le pasó el docente** (se llama `4_Kit_Agente_WhatsApp/` o `6_Agente_WhatsApp/`).
3. **GitHub** (repositorio público, no pide cuenta): descargue
   `https://github.com/Alexey0424/Aula_IA_UNAC/archive/refs/heads/main.zip`, descomprímalo en una
   carpeta temporal y tome `Aula_IA_UNAC-main/6_Agente_WhatsApp/`. O, si hay git:
   `git clone --depth 1 https://github.com/Alexey0424/Aula_IA_UNAC.git`.

**La copia de trabajo** (donde se instala y se configura) va en:
- `<aula>/mis_entregas/agente_whatsapp/` si tiene el aula (esa carpeta nunca se sube), o
- `Documentos/Agente_WhatsApp/` del usuario (Windows: `%USERPROFILE%\Documents\Agente_WhatsApp\`;
  Mac: `~/Documents/Agente_WhatsApp/`). **Nunca** en el Escritorio, ni en OneDrive/Dropbox/Google Drive,
  ni en una carpeta compartida: ahí va a quedar la llave del WhatsApp.

Copie `1_Puente/` y `2_Cerebro/` a la copia de trabajo. En adelante, «la copia» es esa carpeta.

## 4. El cerebro, en el Cloudflare del estudiante

En `<copia>/2_Cerebro/`:

1. `npm install` (instala `@cloudflare/puppeteer` 1.4.0, el navegador de Cloudflare).
2. `npx wrangler kv namespace create cerebro-whatsapp-estado` → anote el `id`.
3. Copie `wrangler.ejemplo.toml` como `wrangler.toml` y reemplace lo que dice CAMBIAR:
   - `name = "cerebro-whatsapp-<empresa>"`: minúsculas, sin tildes ni espacios, con guiones, máximo 40 caracteres.
   - `INFORME_URL`: la dirección del informe. `EMPRESA`: el nombre que dio. `CONTEXTO_EXTRA`: sus frases o `""`.
   - El `id` del KV.
   - **No quite** `compatibility_flags = ["nodejs_compat"]` ni el bloque `[browser]`: sin eso no lee el informe.
4. `npx wrangler deploy` → anote la dirección `https://cerebro-whatsapp-<empresa>.<subdominio>.workers.dev`.
5. **La clave del puente.** Genere 32 caracteres al azar y guárdelos en `<copia>/2_Cerebro/clave.txt`
   (se borra al final de la sección 5):
   `node -e "require('fs').writeFileSync('clave.txt', require('crypto').randomBytes(24).toString('base64url'))"`.
   Súbala como secreto **sin mostrarla y sin salto de línea al final** (sirve igual en Windows y Mac):
   ```
   node -e "require('child_process').execSync('npx wrangler secret put CLAVE_PUENTE',{input:require('fs').readFileSync('clave.txt','utf8').trim(),stdio:['pipe','inherit','inherit'],shell:true})"
   ```
   Espere ~10 s a que se propague.
6. **Pruebe el cerebro** con el script de la sección 9 (`probar.mjs`):
   - `estado` → `configurado`: todo en `true` menos `DB` (en nivel 1 es normal).
   - `releer` → `via: "navegador"`, `caracteres` mayor que 500 y el `titulo` del informe. Lea el
     `comienzo` y confirme que es el informe del estudiante. Si dice `html (sin navegador)` o trae muy
     poco texto, mire `error_navegador` y la tabla de problemas.
   - `mensaje "¿Cómo van los indicadores?"` → compare una o dos cifras con la página del informe.
   - `mensaje "Mándame el informe en PDF"` → trae un adjunto; el script lo descarga y confirma que es PDF.
   Cuéntele al estudiante, en dos o tres líneas, qué contestó su agente.

## 5. El puente, en el computador del estudiante

En `<copia>/1_Puente/`:

1. `npm install` (Baileys, qrcode y pino; ~1 minuto).
2. Copie `config.ejemplo.json` como `config.json` y llene:
   - `"worker"`: la dirección del cerebro **+ `/api/mensaje`**.
   - `"clave_puente"`: el contenido de `clave.txt` (escríbalo con un script, sin imprimirlo). Luego borre `clave.txt`.
   - `"agenda"`: `false` (en el nivel 2 se cambia a `true`). Lo demás se deja igual.
3. **El ícono «WhatsApp IA»**:
   - **Windows:** `powershell -ExecutionPolicy Bypass -File crear_accesos.ps1` (o con `-SinArranque` si
     no quiere que arranque con Windows). Crea **un solo ícono, «WhatsApp IA»**, en el escritorio: un clic
     prende el puente y abre el panel; si ya estaba prendido, solo abre el panel. El arranque con Windows
     queda en la carpeta de Inicio: minimizado, sin abrir el navegador.
   - **Mac:** cree `~/Desktop/WhatsApp IA.command` con este contenido y `chmod +x`:
     ```bash
     #!/bin/bash
     cd "<ruta completa de la copia>/1_Puente" && node puente.mjs
     ```
     Para que arranque con el Mac, un LaunchAgent en `~/Library/LaunchAgents/co.unac.puente-whatsapp.plist`
     con `ProgramArguments` = [ruta de `node` (`which node`), `puente.mjs`, `--sin-navegador`],
     `WorkingDirectory` = la carpeta `1_Puente` y `RunAtLoad` = true; cárguelo con `launchctl load`.
4. **Préndalo como lo hará el estudiante:** Windows,
   `Invoke-Item "$([Environment]::GetFolderPath('Desktop'))\WhatsApp IA.lnk"`; Mac,
   `open ~/Desktop/WhatsApp\ IA.command`. Se abre el panel **`http://localhost:3939`** con el QR.
   (La primera vez instala lo que falte, por eso puede tardar un poco.)
5. **El QR. Lo hace el estudiante:** en el celular, WhatsApp → **⋮** o **Configuración** →
   **Dispositivos vinculados** → **Vincular un dispositivo** → apuntar la cámara al QR del panel. El QR se
   renueva solo cada ~20 s. Confirme con `GET http://localhost:3939/estado` → `"conexion": "conectado"`.
   Al conectarse, el puente le manda al estudiante un mensaje de bienvenida en su chat consigo mismo.

## 6. La prueba con el estudiante

Que abra en WhatsApp su **chat consigo mismo** («Mensaje para mí» o «Tú») y escriba:
`hola` · una pregunta sobre su informe · «Mándame el informe en PDF» · y una **nota de voz**.
Las respuestas llegan con 🤖 al comienzo; el PDF llega como documento. Si algo no llega, revise
`eventos` en `http://localhost:3939/estado` y la tabla de problemas.

Explíquele cómo se maneja (estas cinco líneas, tal cual):
- **Ícono «WhatsApp IA»**: abre el panel, y prende el puente si estaba apagado.
- **En el panel**: 🔴 Apagado · 🟢 Solo yo · 🟠 Abierto (se apaga solo a los 15 min) y el botón **Detener**.
- **Desde el celular**, escribiéndose a sí mismo: `bot off` · `bot yo` · `bot estado`.
- Arranca en el **último modo** en que lo dejó (el Abierto vuelve como Solo yo).
- Si el computador se apaga o se suspende, el bot se calla; al volver, se reconecta solo.

## 7. Nivel 2 (opcional): la agenda

Solo si el estudiante lo pide.

1. En `<copia>/2_Cerebro/`: `npx wrangler d1 create agenda-whatsapp` → anote el `database_id`.
2. `npx wrangler d1 execute agenda-whatsapp --remote --file esquema_agenda.sql`.
3. En `wrangler.toml` quite los `#` del bloque `[[d1_databases]]` y ponga el id. `npx wrangler deploy`.
4. En `<copia>/1_Puente/config.json`: `"agenda": true`. Reinicie el puente (botón **Detener** del panel y
   luego el ícono «WhatsApp IA»).
5. Pruebe con `probar.mjs` y luego por WhatsApp: «Agéndame una cita mañana a las 3 con Julián de Argos» ·
   «¿Qué tengo esta semana?» · «Anota que Julián pidió 5 % de descuento» · «¿Qué hemos hablado con Julián?» ·
   «Cancela la de Argos». El agente pregunta el día o la hora si faltan; no los inventa. Treinta minutos
   antes de cada cita llega un ⏰ al chat consigo mismo.
6. **Pintar la agenda en el informe (opcional).** Advierta antes: **si el informe es público, la agenda
   también lo es**; con clientes reales, mejor no pintarla y consultarla solo por WhatsApp. Si insiste:
   pegue el contenido de `3_Agenda_en_el_Informe/agenda_widget.html` en el HTML de **su informe** (en la
   carpeta del proyecto del informe de la Clase 07, nunca en el aula ni en el kit), cambie la variable
   `CEREBRO` por la dirección del cerebro y vuelva a publicar el informe con el mismo comando de la Clase 07.

## 8. Lo que el cerebro expone (para probar y diagnosticar)

| Ruta | Método | Clave (`x-clave`) | Qué hace |
|---|---|---|---|
| `/api/mensaje` | POST | Sí | Lo que usa el puente. Cuerpo: `{"texto": "...", "conversacion": "id", "memoria_en_puente": true, "estado_conversacion": {...}}` o `{"audio_base64": "..."}`. Responde `{ok, respuesta, adjuntos, transcripcion, ruta, estado_conversacion}` |
| `/api/releer` | GET | Sí | Vuelve a leer el informe ya y muestra cómo lo leyó |
| `/api/recordatorios` | GET | Sí | Nivel 2: citas que empiezan en los próximos 30 min (cada una se avisa una vez) |
| `/api/estado` | GET | No | Qué está configurado, las tools y la última lectura (sin secretos) |
| `/informe.pdf` | GET | No | El PDF del informe |
| `/api/agenda` | GET | No | Nivel 2: las próximas citas (para pintarlas en el informe) |

El puente guarda la **memoria corta** de cada chat (30 min) y se la devuelve al cerebro en cada mensaje
(`estado_conversacion`): así «a las 3» se entiende después de «¿a qué hora?».

## 9. Script de prueba (`probar.mjs`)

Guárdelo en `<copia>/2_Cerebro/probar.mjs`. Uso:
`node probar.mjs <dirección del cerebro> <archivo con la clave> estado|releer|pdf|"mensaje 1" "mensaje 2" ...`

```js
// probar.mjs · prueba el cerebro como lo hace el puente (clave + memoria corta).
import fs from "node:fs";
const [W, archivoClave, ...pasos] = process.argv.slice(2);
const clave = fs.readFileSync(archivoClave, "utf8").trim();
const H = { "content-type": "application/json", "x-clave": clave };
let memoria = null;
for (const p of pasos) {
  if (p === "estado" || p === "releer") {
    const r = await fetch(W + "/api/" + p, { headers: H });
    const d = await r.json();
    if (d.comienzo) d.comienzo = d.comienzo.slice(0, 300) + "…";
    console.log("### " + p, "HTTP " + r.status, JSON.stringify(d, null, 2).slice(0, 1500));
    continue;
  }
  const r = await fetch(W + "/api/mensaje", {
    method: "POST", headers: H,
    body: JSON.stringify({ texto: p, conversacion: "prueba_claude", memoria_en_puente: true, estado_conversacion: memoria }),
  });
  const d = await r.json();
  if (d.estado_conversacion) memoria = d.estado_conversacion;
  console.log("### " + p + "\n[" + (d.ms || "?") + " ms · " + (d.ruta ? d.ruta.accion + " · " + d.ruta.via : "") + "]\n" + (d.respuesta || d.error));
  for (const a of d.adjuntos || []) {
    const f = await fetch(a.url);
    console.log("ADJUNTO " + a.nombre + ": HTTP " + f.status + " · " + f.headers.get("content-type") + " · " + (await f.arrayBuffer()).byteLength + " bytes");
  }
  console.log();
}
```

Bórrelo junto con `clave.txt` cuando termine (la clave queda en `config.json` del puente).

## 10. Límites que el estudiante debe saber

- **El computador tiene que estar prendido** y sin suspenderse para que el bot conteste.
- **Workers AI gratis: 10.000 neurons al día por cuenta,** que se recargan a las **7:00 p. m. hora de
  Colombia** (00:00 UTC). En cada pregunta el modelo lee el informe completo (hasta 18.000 caracteres):
  del orden de 150 a 300 neurons por pregunta, así que alcanza para unas decenas de mensajes al día.
  Si se agotan, el bot contesta «El modelo de IA no respondió». **No haga pruebas largas** el mismo día
  en que el estudiante lo va a mostrar.
- **Navegador de Cloudflare gratis:** 10 minutos al día y un navegador nuevo cada 20 s. Por eso el
  informe se relee cada 15 minutos y el PDF se rehace cada hora.
- **Si el estudiante cambia su informe**, el agente lo ve a los 15 minutos, o de una con `releer`.
- Lo que una gráfica pinta **sin el número escrito** el agente no lo puede leer; sí lee tarjetas, tablas
  y los datos que trae el código de la página.

## 11. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `wrangler` dice `Authentication error [code: 10000]` | El token de la Clase 07 no tiene permisos de KV/D1 | Quitar `CLOUDFLARE_API_TOKEN` del entorno y `npx wrangler login` |
| `releer` dice `html (sin navegador)` | Navegador ocupado (límite gratis) o falta `nodejs_compat` / `[browser]` | Esperar 1 minuto; revisar `wrangler.toml` y volver a desplegar |
| `releer` trae el título de otra página | `INFORME_URL` equivocada | Corregir, `npx wrangler deploy`, `releer` |
| `mensaje` responde 401 | La clave del secreto y la de `config.json` no son la misma | Volver a hacer el paso 4.5 y el 5.2 con la misma clave |
| `mensaje` responde 500 «Falta el secreto CLAVE_PUENTE» | No se subió el secreto, o aún se propaga | Paso 4.5; esperar 10 s |
| «El modelo de IA no respondió» | Se acabaron los neurons del día | Esperar a las 7:00 p. m. hora de Colombia |
| ⏳ al pedir el PDF | Límite del navegador gratis | Pedirlo otra vez en un minuto |
| El panel no abre / «esperando QR» y no aparece | El puente arrancó escondido con Windows | Abrir el ícono «WhatsApp IA» |
| «reemplazada» en el panel | Dos puentes con la misma sesión | Detener todo y abrir el ícono una sola vez |
| «desvinculado» | Lo sacaron de Dispositivos vinculados | Botón «Vincular de nuevo» y escanear |
| ⚠️ «No pude consultar el informe en Cloudflare» en WhatsApp | `worker` o `clave_puente` mal en `config.json` | Revisar contra el cerebro con `probar.mjs` |
| El puerto 3939 está ocupado | Otro programa lo usa | Cambiar `"puerto"` en `config.json` y en `2_DETENER_PUENTE.bat` |

## 12. Desmontar (solo si el estudiante lo pide)

- Windows: en `<copia>/1_Puente/`, `powershell -ExecutionPolicy Bypass -File crear_accesos.ps1 -Quitar`
  (quita el ícono y el arranque). Mac: borrar el `.command` y el LaunchAgent (`launchctl unload`).
- En el panel, **Desvincular** (sale de Dispositivos vinculados) y **Detener**.
- Cloudflare: en `<copia>/2_Cerebro/`, `npx wrangler delete`; borrar el KV y la D1 si se crearon.
- Borrar la copia de trabajo.

## 13. Al terminar, el resumen para el estudiante

En cinco líneas: la dirección de su cerebro, qué le contestó a la pregunta de prueba, cómo se prende y
apaga (el ícono y el panel), cuántos mensajes al día le alcanzan, y el recordatorio de que
`sesion_whatsapp/` es la llave de su WhatsApp.
