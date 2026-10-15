---
name: agente-whatsapp
description: Conectar el informe publicado del estudiante a su WhatsApp con el kit 6_Agente_WhatsApp (puente semihibrido en su computador + cerebro en su Cloudflare), paso a paso y sin que el estudiante escriba comandos. Usar cuando el estudiante pida conectar su informe o tablero a WhatsApp, montar el agente de WhatsApp, activar la agenda (nivel 2), o prender, apagar, desmontar o arreglar el puente.
---

# Agente de WhatsApp sobre el informe · Clase 12

El estudiante ya tiene su **informe HTML publicado en Cloudflare** (Clase 07). Esto lo conecta a
**su WhatsApp** para preguntarle al informe por texto o nota de voz y pedirle el PDF. Tres piezas:

```
su celular ─► su PC: PUENTE (1_Puente, Baileys, dispositivo vinculado) ─► su Cloudflare: CEREBRO (2_Cerebro)
                                                                              └─► lee SU informe publicado
```

- El **puente** es igual para todos. El **cerebro** es una plantilla que se ajusta solo con
  `wrangler.toml`: el código no se toca. El **informe** no se modifica (salvo el nivel 2 opcional).
- El cerebro **lee el informe abriéndolo en un navegador de Cloudflare**: lo que se ve, las
  pestañas ocultas y los datos que trae el código. Por eso sirve para cualquier informe.
- Todo el detalle técnico está en `6_Agente_WhatsApp/LEEME.md`. Léalo antes de empezar.

## Reglas que no se negocian

1. **El estudiante no escribe comandos.** Usted los corre todos. Él solo hace dos cosas:
   autorizar Cloudflare en el navegador (si hace falta) y **escanear el QR** con el celular.
2. **Nada del estudiante se escribe dentro de `6_Agente_WhatsApp/`**: es material del curso y
   se rompería el `git pull`. Su copia va en **`mis_entregas/agente_whatsapp/`** (no se sube nunca).
3. **`sesion_whatsapp/` y `config.json` son llaves.** Quien copie `sesion_whatsapp/` entra al
   WhatsApp del estudiante. Nunca se muestran, no se copian a otro lado, no van a GitHub, no se
   pegan en el chat. La `CLAVE_PUENTE` no se imprime en pantalla.
4. **Modo de clase: «Solo yo»** (el bot solo contesta en el chat del estudiante consigo mismo).
   No active el modo Abierto ni `numeros_permitidos` si el estudiante no lo pide y entiende el riesgo.
5. **Antes de empezar, dígale el riesgo en dos líneas:** el puente es un cliente **no oficial** de
   WhatsApp; usarlo va contra los términos de servicio de WhatsApp y puede terminar en bloqueo del
   número. Es un ejercicio de clase en modo «Solo yo». Si tiene un segundo número, mejor.
6. **Pruebe con Node, no con curl,** cuando mande texto con tildes o ñ: desde Git Bash en Windows
   curl daña la codificación y las pruebas dan resultados falsos.

## Paso 0 · Verificar antes de tocar nada

1. **Sistema operativo** (Windows o Mac) y **Node.js**: `node --version` (sirve 20 o más).
   Si falta: Windows `winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements`
   (después use la ruta completa `"C:\Program Files\nodejs\node.exe"` o abra otra terminal);
   Mac `brew install node` o el instalador de nodejs.org.
2. **La dirección del informe.** Viene en el prompt; si no, pídasela. Ábrala (petición GET) y
   confirme que responde 200 y que el título es el de su informe.
3. **Cloudflare.** `npx wrangler whoami`. Si el estudiante tiene el `.env` de la Clase 07 con
   `CLOUDFLARE_API_TOKEN`, cárguelo como variable de entorno (sin imprimirlo). Si no hay sesión, o
   si al crear el KV sale un error de permisos (`Authentication error [code: 10000]`), quite esa
   variable del entorno y corra `npx wrangler login`: se abre el navegador y el estudiante da
   clic en **Allow**. Esa es la autorización de Cloudflare.
4. **Pregúntele** (en un solo mensaje):
   - el nombre de la empresa tal como quiere verlo en WhatsApp;
   - opcional, una o dos frases de contexto para leer bien sus números (qué es bueno y qué es malo,
     qué periodo cubre). Si en la Clase 08 llenó el CAMPO 5 del prompt, sirve tal cual;
   - si quiere solo el **nivel 1** (preguntas + PDF, el de la clase) o también el **nivel 2** (agenda).

## Paso 1 · Copiar el kit

Desde la carpeta del aula: copie `6_Agente_WhatsApp/1_Puente/` y `6_Agente_WhatsApp/2_Cerebro/`
a `mis_entregas/agente_whatsapp/1_Puente/` y `mis_entregas/agente_whatsapp/2_Cerebro/`.

**Si el estudiante no tiene el aula** y recibió el kit en una carpeta (por Moodle o por WhatsApp,
con este archivo como `INSTRUCCIONES_PARA_CLAUDE.md`): tome `1_Puente/` y `2_Cerebro/` de esa
carpeta y haga la copia de trabajo en `Documentos/Agente_WhatsApp/` del usuario (en Windows,
`%USERPROFILE%\Documents\Agente_WhatsApp\`). Nunca en el Escritorio ni en una carpeta que se
sincronice o se comparta. Donde esta guía dice `6_Agente_WhatsApp/`, es la carpeta del kit que recibió.

## Paso 2 · El cerebro, en el Cloudflare del estudiante

En `mis_entregas/agente_whatsapp/2_Cerebro/`:

1. `npm install` (instala `@cloudflare/puppeteer`, el navegador de Cloudflare).
2. `npx wrangler kv namespace create cerebro-whatsapp-estado` → anote el `id`.
3. Copie `wrangler.ejemplo.toml` como `wrangler.toml` y llene lo que dice CAMBIAR:
   `name = "cerebro-whatsapp-<empresa>"` (minúsculas, sin tildes ni espacios, máximo 40 caracteres),
   `INFORME_URL`, `EMPRESA`, `CONTEXTO_EXTRA` (o vacío) y el `id` del KV.
4. `npx wrangler deploy` → anote la dirección `https://cerebro-whatsapp-<empresa>.<subdominio>.workers.dev`.
5. **La clave del puente:** genere 32 caracteres al azar
   (`node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))"`), guárdela en
   un archivo temporal y súbala como secreto sin mostrarla: `npx wrangler secret put CLAVE_PUENTE`
   (pasándola por la entrada estándar). La misma clave va en `config.json` del puente (paso 3).
   Espere ~10 s a que se propague.
6. **Pruebas del cerebro** (con un script de Node que mande la cabecera `x-clave`):
   - `GET /api/estado` → `configurado` todo en ✔ menos `DB` (en nivel 1 es normal).
   - `GET /api/releer` → `via: "navegador"`, `caracteres` > 500 y el `titulo` del informe. Lea el
     `comienzo` y confirme que es el informe del estudiante. Si dice `html (sin navegador)` o trae
     muy poco texto, mire `error_navegador` (ver la tabla de problemas).
   - `POST /api/mensaje` con `{"texto": "¿Cómo van los indicadores?", "memoria_en_puente": true}` →
     compare una o dos cifras de la respuesta con la página del informe.
   - `POST /api/mensaje` con `{"texto": "Mándame el informe en PDF", "memoria_en_puente": true}` →
     trae `adjuntos[0].url`; descárguela y confirme `application/pdf`.
   Cuéntele al estudiante, en dos líneas, qué contestó su agente.

## Paso 3 · El puente, en el computador del estudiante

En `mis_entregas/agente_whatsapp/1_Puente/`:

1. `npm install` (Baileys, qrcode y pino: ~1 minuto).
2. Copie `config.ejemplo.json` como `config.json`: `worker` = la dirección del cerebro +
   `/api/mensaje`, `clave_puente` = la clave del paso 2, `agenda` = `false`.
3. **El ícono.** Pregúntele si quiere que el puente **arranque solo al prender el computador**.
   - **Windows:** `powershell -ExecutionPolicy Bypass -File crear_accesos.ps1` (o con
     `-SinArranque` si no lo quiere). Crea **un solo ícono, «WhatsApp IA»**, en el escritorio: un
     clic prende el puente y abre el panel; si ya estaba prendido, solo abre el panel.
   - **Mac:** cree `~/Desktop/WhatsApp IA.command` con
     `#!/bin/bash` + `cd "<ruta de 1_Puente>"` + `node puente.mjs` y `chmod +x`. Para que arranque con
     el Mac, un LaunchAgent en `~/Library/LaunchAgents/co.unac.puente-whatsapp.plist` con
     `ProgramArguments` = [ruta de node, `puente.mjs`, `--sin-navegador`], `WorkingDirectory` = la
     carpeta del puente y `RunAtLoad` = true. Pruébelo con `launchctl load`.
4. **Préndalo como lo hará el estudiante:** Windows, abriendo el ícono
   (`Invoke-Item "$([Environment]::GetFolderPath('Desktop'))\WhatsApp IA.lnk"`); Mac,
   `open ~/Desktop/WhatsApp\ IA.command`. Se abre el panel `http://localhost:3939` con el QR.
5. **El QR (lo hace el estudiante):** en el celular, WhatsApp → ⋮ o Configuración →
   **Dispositivos vinculados** → **Vincular un dispositivo** → apuntar al QR del panel. El QR se
   renueva solo cada ~20 s. Confirme con `GET http://localhost:3939/estado` → `conexion: "conectado"`.

## Paso 4 · La prueba con el estudiante

Que abra en WhatsApp su **chat consigo mismo** («Mensaje para mí» / «Tú») y escriba:
`hola` · una pregunta sobre su informe · «Mándame el informe en PDF» · y una **nota de voz**.
Las respuestas llegan con 🤖 al comienzo. Revise los eventos en `/estado` si algo no llega.

Explíquele cómo se maneja, en cinco líneas:
- **Ícono «WhatsApp IA»**: abre el panel (y prende el puente si estaba apagado).
- **En el panel**: 🔴 Apagado · 🟢 Solo yo · 🟠 Abierto (se apaga solo a los 15 min) y **Detener**.
- **Desde el celular**, escribiéndose a sí mismo: `bot off` · `bot yo` · `bot estado`.
- Arranca en el **último modo** en que lo dejó (el Abierto vuelve como Solo yo).
- Si el computador se apaga o se suspende, el bot se calla; al volver, se reconecta solo.

## Paso 5 (opcional) · Nivel 2: la agenda

1. `npx wrangler d1 create agenda-whatsapp` → anote el `database_id`.
2. `npx wrangler d1 execute agenda-whatsapp --remote --file esquema_agenda.sql`.
3. En `wrangler.toml` quite los `#` del bloque `[[d1_databases]]` y ponga el id. `npx wrangler deploy`.
4. En `config.json` del puente: `"agenda": true`. Reinicie el puente (Detener en el panel y el ícono).
5. Pruebe: «Agéndame una cita mañana a las 3 con Julián de Argos» · «¿Qué tengo esta semana?» ·
   «Anota que Julián pidió 5 % de descuento» · «¿Qué hemos hablado con Julián?» · «Cancela la de
   Argos». Treinta minutos antes de cada cita llega un ⏰ al chat consigo mismo.
6. **Pintar la agenda en el informe (opcional).** Advierta antes: **si el informe es público, la
   agenda también lo es**; con clientes reales, mejor no pintarla y consultarla solo por WhatsApp. Si
   quiere: pegue `6_Agente_WhatsApp/3_Agenda_en_el_Informe/agenda_widget.html` en el HTML del
   informe (en la carpeta del proyecto del informe, nunca en el aula), cambie `CEREBRO` por la
   dirección del cerebro y vuelva a publicar el informe como lo hizo en la Clase 07.

## Límites que el estudiante debe saber

- **El computador tiene que estar prendido** (y sin suspenderse) para que el bot conteste.
- **Workers AI gratis: 10.000 neurons al día por cuenta**, que se recargan a las 7:00 p. m. hora
  de Colombia (00:00 UTC). Cada pregunta sobre el informe gasta del orden de 150 a 300 neurons,
  porque el modelo lee el informe completo en cada mensaje: alcanza para unas decenas de mensajes
  al día, no para cientos. Si se agotan, el bot contesta «el modelo no respondió».
- **Navegador de Cloudflare gratis:** 10 minutos al día y un navegador nuevo cada 20 s. Por eso
  el informe se relee cada 15 minutos y el PDF se rehace cada hora.
- **Si el estudiante cambia su informe**, el agente lo ve a los 15 minutos, o de una con `GET /api/releer`.
- Lo que el informe pinta en una gráfica **sin el número escrito** el agente no lo puede leer:
  sí lee las tarjetas, las tablas y los datos que trae el código de la página.

## Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El panel dice «esperando QR» y el QR no aparece | Arrancó escondido con Windows | Abrir el ícono «WhatsApp IA» |
| «reemplazada» en el panel | Hay dos puentes con la misma sesión | Detener todo y abrir el ícono una sola vez |
| «desvinculado» | Lo sacaron de Dispositivos vinculados | Botón «Vincular de nuevo» y escanear |
| ⚠️ «No pude consultar el informe en Cloudflare» | `worker` o `clave_puente` mal en `config.json` | Revisar contra el cerebro (401 = clave) |
| «El modelo de IA no respondió» | Se acabaron los neurons del día | Esperar a las 7:00 p. m. |
| `/api/releer` dice `html (sin navegador)` | Navegador ocupado (429) o sin `compatibility_flags = ["nodejs_compat"]` | Esperar 1 minuto; revisar `wrangler.toml` |
| El agente contesta cosas de otro informe | `INFORME_URL` equivocada | Corregir y `npx wrangler deploy`, luego `/api/releer` |
| ⏳ en el PDF | Límite del navegador gratis | Pedirlo otra vez en un minuto |

## Desmontar (si el estudiante lo pide)

En `1_Puente/`: `crear_accesos.ps1 -Quitar` (quita el ícono y el arranque) · en el panel,
**Desvincular** (sale de Dispositivos vinculados) · borrar `mis_entregas/agente_whatsapp/`.
En Cloudflare: `npx wrangler delete` en `2_Cerebro/`, y el KV y la D1 si se crearon.
