/* ===========================================================================
   PUENTE SEMIHIBRIDO: SU WHATSAPP -> ESTE COMPUTADOR -> CLOUDFLARE
   Diplomado en Inteligencia Artificial · UNAC · Clase 12
   ===========================================================================
   La idea en una frase: la PUERTA de WhatsApp vive en este computador y el
   CEREBRO sigue en Cloudflare: el Worker cuya direccion esta en config.json
   ("worker"). Este programa es igual para todos; lo que cambia es el cerebro.

     su celular --(dispositivo vinculado, como WhatsApp Web)--> ESTE PROGRAMA
        1. recibe el mensaje (texto o nota de voz)
        2. se lo manda al Worker por POST   (sale a internet; no hace falta
           abrir puertos ni tunel, porque el que llama es este PC)
        3. el Worker transcribe, decide con un LLM y consulta el informe
        4. este programa contesta en el mismo chat de WhatsApp

   PRENDER Y APAGAR SIN CLAUDE: los iconos del escritorio (los crea
   crear_accesos.ps1) o los .bat de esta carpeta. Solo puede haber UN puente
   prendido: si ya hay uno, este abre el panel y se cierra. Arranca en el
   ultimo modo en que se dejo (modo_guardado.json), salvo "abierto", que es
   temporal y vuelve como "solo_yo".

   POR QUE "SEMIHIBRIDO": la API oficial de Meta exige negocio verificado y
   tarjeta (Clase 10, error #131031). Esta via entra como dispositivo
   vinculado (libreria Baileys) y por eso necesita un computador prendido:
   la conexion con WhatsApp tiene que quedarse abierta todo el tiempo, y un
   Worker solo vive lo que dura una peticion.

   EL INTERRUPTOR (es un numero personal: el bot solo habla un momentico)
     apagado  -> no le contesta a nadie (sigue vinculado, solo escucha ordenes)
     solo_yo  -> solo el chat consigo mismo + numeros_permitidos.  ARRANCA ASI.
     abierto  -> cualquier chat individual que le escriba. Se apaga SOLO a los
                 minutos_modo_abierto y vuelve a solo_yo.
   Nunca contesta grupos, estados ni canales, en ningun modo.

   Se cambia desde el celular, escribiendose a si mismo:
     bot off · bot yo · bot abierto · bot abierto 5 · bot estado
   o con los botones de la pagina local. Cerrar la ventana tambien lo apaga:
   el celular sigue funcionando normal.

   OJO: usar WhatsApp por un cliente no oficial va contra sus terminos de
   servicio y puede terminar en bloqueo del numero. Esto es un intento de
   clase, no una instalacion para clientes (para eso: API oficial de Meta).
   =========================================================================== */

import makeWASocket, {
  Browsers,
  DisconnectReason,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  isJidBroadcast,
  isJidGroup,
  isJidNewsletter,
  isPnUser,
  jidNormalizedUser,
  normalizeMessageContent,
  useMultiFileAuthState,
} from "baileys";
import QRCode from "qrcode";
import pino from "pino";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { exec } from "node:child_process";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
if (!fs.existsSync(path.join(AQUI, "config.json"))) {
  console.error("Falta config.json en " + AQUI + ". Se crea copiando config.ejemplo.json y poniendo la dirección del Worker.");
  process.exit(1);
}
const CONFIG = JSON.parse(fs.readFileSync(path.join(AQUI, "config.json"), "utf8"));
const PANEL = "http://localhost:" + CONFIG.puerto;

// La carpeta de la sesion ES la llave de su WhatsApp: quien la copie, entra.
// No se sube a ningun lado, no se comparte y no va al aula.
const SESION = path.join(AQUI, "sesion_whatsapp");
const MODO_GUARDADO = path.join(AQUI, "modo_guardado.json");

const MARCA = CONFIG.marca_bot || "🤖";
const PERMITIDOS = new Set((CONFIG.numeros_permitidos || []).map((n) => String(n).replace(/\D/g, "")).filter(Boolean));
const MINUTOS_ABIERTO = Number(CONFIG.minutos_modo_abierto) || 15;
const PLAZO_MS = 90000; // el analisis completo tarda 8-25 s; se deja margen
// Recordatorios de citas: solo si el cerebro tiene agenda (nivel 2) y hay clave.
const CON_AGENDA = !!CONFIG.clave_puente && (CONFIG.agenda ?? true);

const logger = pino({ level: "error" });

// Abre el panel en el navegador (Windows, Mac o Linux).
function abrirPanel() {
  const cmd = process.platform === "win32" ? 'start "" ' : process.platform === "darwin" ? "open " : "xdg-open ";
  exec(cmd + PANEL);
}

// UN SOLO PUENTE. Dos puentes con la misma sesion se tumban entre si
// ("reemplazada"). Si ya hay uno prendido, este solo abre el panel y se va.
try {
  const r = await fetch(PANEL + "/estado", { signal: AbortSignal.timeout(1500) });
  if (r.ok) {
    console.log("El puente ya está prendido. Abro el panel: " + PANEL);
    abrirPanel();
    setTimeout(() => process.exit(0), 500);
    await new Promise(() => {}); // no sigue: espera la salida
  }
} catch { /* no hay otro puente: seguimos */ }

// ---------------------------------------------------------------------------
// ESTADO (lo que muestra la pagina local http://localhost:PUERTO)
// ---------------------------------------------------------------------------
// El ultimo modo en que se dejo. "abierto" no se recuerda: es temporal.
function modoInicial() {
  try {
    const m = JSON.parse(fs.readFileSync(MODO_GUARDADO, "utf8")).modo;
    return m === "apagado" ? "apagado" : "solo_yo";
  } catch { return "solo_yo"; }
}

const estado = {
  conexion: "iniciando", // iniciando | esperando_qr | conectado | reconectando | sesion_cerrada | desvinculado | reemplazada
  modo: modoInicial(),   // apagado | solo_yo | abierto
  abiertoHasta: null,
  qr: null,              // imagen del QR (data URL) mientras se espera el escaneo
  yo: null,              // numero vinculado, enmascarado
  desde: null,
  eventos: [],           // bitacora corta: no guarda el texto de los mensajes
};

const enmascarar = (num) => (num ? String(num).replace(/\d(?=\d{4})/g, "•") : "");

function anotar(evento) {
  estado.eventos.unshift({ cuando: new Date().toISOString(), ...evento });
  estado.eventos = estado.eventos.slice(0, 20);
  const e = estado.eventos[0];
  console.log(`[${e.cuando.slice(11, 19)}] ${e.chat || ""} ${e.tipo || ""} ${e.accion || ""} ${e.resultado || ""} ${e.ms ? e.ms + " ms" : ""} ${e.error || ""}`.replace(/\s+/g, " "));
}

// ---------------------------------------------------------------------------
// EL CEREBRO ESTA EN CLOUDFLARE: se le pregunta y se espera la respuesta.
// ---------------------------------------------------------------------------
// La conversacion se identifica con una huella del chat, no con el numero:
// el Worker recuerda los ultimos turnos sin saber de quien son.
const huellaChat = (chat) => createHash("sha256").update("puente:" + chat).digest("hex").slice(0, 24);

// MEMORIA CORTA DE CADA CHAT: la guarda el puente y se la devuelve al cerebro en
// cada mensaje (30 min). En Cloudflare KV tardaba hasta un minuto en verse, y con
// una respuesta rapida ("a las 3") el agente olvidaba la pregunta anterior.
// Si el cerebro no la maneja (no devuelve estado_conversacion), no pasa nada.
const conversaciones = new Map(); // huella del chat -> { estado, ts }

async function preguntarAlWorker(cuerpo, chat) {
  const conv = huellaChat(chat);
  const guardada = conversaciones.get(conv);
  const estadoConv = guardada && Date.now() - guardada.ts < 30 * 60000 ? guardada.estado : null;
  const r = await fetch(CONFIG.worker, {
    method: "POST",
    headers: { "content-type": "application/json", ...(CONFIG.clave_puente ? { "x-clave": CONFIG.clave_puente } : {}) },
    body: JSON.stringify({ ...cuerpo, canal: "puente", conversacion: conv, memoria_en_puente: true, estado_conversacion: estadoConv }),
    signal: AbortSignal.timeout(PLAZO_MS),
  });
  const d = await r.json().catch(() => ({ ok: false, error: "El Worker respondió algo que no es JSON (HTTP " + r.status + ")" }));
  if (!d.ok) throw new Error(d.error || "El Worker respondió con error");
  if (d.estado_conversacion) {
    conversaciones.set(conv, { estado: d.estado_conversacion, ts: Date.now() });
    if (conversaciones.size > 200) conversaciones.delete(conversaciones.keys().next().value);
  }
  return d;
}

// ---------------------------------------------------------------------------
// WHATSAPP
// ---------------------------------------------------------------------------
let sock = null;
let miChat = null;                // su propio numero: el chat "Mensaje para mi"
let misJids = new Set();          // su numero y su LID, sin dispositivo
let desvinculadoAMano = false;
const enviadosPorElBot = new Set(); // ids de lo que contesto el bot (no contestarse a si mismo)
const vistos = new Set();         // ids ya atendidos (no contestar dos veces)
const cache = new Map();          // mensajes enviados, por si WhatsApp pide reenviarlos
const ARRANQUE = Math.floor(Date.now() / 1000);
let cola = Promise.resolve();     // un mensaje a la vez
let intentos = 0;
let relojAbierto = null;
let yaSaludo = false;          // el aviso de "conectado" va una sola vez por arranque
let panelAbierto = false;      // si arranco con --sin-navegador, el panel se abre solo cuando hay QR

const recordar = (set, id, max = 500) => {
  set.add(id);
  if (set.size > max) set.delete(set.values().next().value);
};

function textoDe(contenido) {
  return (
    contenido?.conversation ||
    contenido?.extendedTextMessage?.text ||
    contenido?.imageMessage?.caption ||
    contenido?.documentMessage?.caption ||
    ""
  ).trim();
}

function anotarEnviado(enviado) {
  if (enviado?.key?.id) {
    recordar(enviadosPorElBot, enviado.key.id);
    cache.set(enviado.key.id, enviado.message);
    if (cache.size > 200) cache.delete(cache.keys().next().value);
  }
}

async function enviar(chat, texto, citado) {
  anotarEnviado(await sock.sendMessage(chat, { text: MARCA + " " + texto }, citado ? { quoted: citado } : {}));
}

// El PDF del informe: se baja de Cloudflare y se manda como documento de
// WhatsApp, con la respuesta del agente como pie.
async function enviarDocumento(chat, adjunto, pie, citado) {
  const r = await fetch(adjunto.url, { signal: AbortSignal.timeout(PLAZO_MS) });
  if (!r.ok) throw new Error("No se pudo bajar " + adjunto.nombre + " (HTTP " + r.status + ")");
  const archivo = Buffer.from(await r.arrayBuffer());
  anotarEnviado(await sock.sendMessage(chat, {
    document: archivo,
    mimetype: adjunto.mimetype || "application/pdf",
    fileName: adjunto.nombre || "documento.pdf",
    caption: MARCA + " " + pie,
  }, citado ? { quoted: citado } : {}));
}

// Aviso en el chat consigo mismo (si esta conectado). Nunca tumba nada.
const avisarme = (texto) => (sock && miChat && estado.conexion === "conectado" ? enviar(miChat, texto).catch(() => {}) : Promise.resolve());

// ---------------------------------------------------------------------------
// EL INTERRUPTOR
// ---------------------------------------------------------------------------
function describirModo() {
  if (estado.modo === "apagado") return "🔴 *Apagado*: no le contesto a nadie. Escriba «bot yo» o «bot abierto» para prenderme.";
  if (estado.modo === "solo_yo") return "🟢 *Solo usted*: contesto únicamente en este chat" + (PERMITIDOS.size ? " y a " + PERMITIDOS.size + " número(s) permitido(s)" : "") + ".";
  const min = Math.max(1, Math.round((estado.abiertoHasta - Date.now()) / 60000));
  return "🟠 *Abierto*: le contesto a cualquiera que le escriba por chat individual, durante " + min + " min más. «bot off» para cortar ya.";
}

function cambiarModo(modo, origen, minutos) {
  clearTimeout(relojAbierto);
  estado.modo = modo;
  estado.abiertoHasta = null;
  if (modo === "abierto") {
    const min = Math.min(120, Math.max(1, Number(minutos) || MINUTOS_ABIERTO));
    estado.abiertoHasta = Date.now() + min * 60000;
    relojAbierto = setTimeout(() => {
      cambiarModo("solo_yo", "reloj");
      avisarme("⏱️ Se acabó el modo abierto. Ya solo le contesto en este chat.");
    }, min * 60000);
  }
  try { fs.writeFileSync(MODO_GUARDADO, JSON.stringify({ modo: modo === "apagado" ? "apagado" : "solo_yo" })); } catch { /* no tumba nada */ }
  anotar({ chat: "yo", tipo: "interruptor", accion: modo, resultado: "desde " + origen });
}

// Ordenes que se escriben en el chat consigo mismo. Llevan "bot" adelante
// para que una pregunta normal nunca se confunda con una orden.
function leerOrden(texto) {
  const m = /^bot\s+(off|apagar|apagado|on|yo|solo yo|encender|abierto|abrir|todos|estado)(?:\s+(\d+))?\s*$/i.exec(texto.trim());
  if (!m) return null;
  const p = m[1].toLowerCase();
  if (["off", "apagar", "apagado"].includes(p)) return { modo: "apagado" };
  if (["on", "yo", "solo yo", "encender"].includes(p)) return { modo: "solo_yo" };
  if (["abierto", "abrir", "todos"].includes(p)) return { modo: "abierto", minutos: m[2] };
  return { modo: null };
}

// Lo que una persona manda de verdad. Todo lo demas se ignora en silencio:
// el celular usa el chat consigo mismo para mandarle al dispositivo vinculado
// mensajes internos (protocolMessage: llaves, avisos de sincronizacion), y
// tambien llegan reacciones, ediciones, encuestas... Nada de eso es para el bot.
const MEDIOS = ["imageMessage", "videoMessage", "documentMessage", "documentWithCaptionMessage", "stickerMessage", "locationMessage", "contactMessage"];
function esDePersona(contenido) {
  if (!contenido || contenido.protocolMessage || contenido.reactionMessage) return false;
  return !!(textoDe(contenido) || contenido.audioMessage || MEDIOS.some((m) => contenido[m]));
}

// Decide que hacer con un mensaje: { quien, orden? } o null si no es para el bot.
function clasificar(msg) {
  const k = msg.key || {};
  const chat = k.remoteJid || "";
  if (!chat || isJidGroup(chat) || isJidBroadcast(chat) || isJidNewsletter(chat)) return null;
  if (enviadosPorElBot.has(k.id)) return null; // el eco de lo que el bot acaba de mandar
  const contenido = normalizeMessageContent(msg.message);
  if (!esDePersona(contenido)) return null;

  const esChatConsigoMismo = [chat, k.remoteJidAlt].some((j) => j && misJids.has(jidNormalizedUser(j)));
  if (esChatConsigoMismo) {
    if (!k.fromMe) return null;
    const t = textoDe(contenido);
    if (t.startsWith(MARCA)) return null; // es una respuesta del propio bot
    const orden = leerOrden(t);
    if (orden) return { quien: "yo", orden };         // las ordenes valen aun apagado
    return estado.modo === "apagado" ? null : { quien: "yo" };
  }

  if (k.fromMe || estado.modo === "apagado") return null;
  const pn = [chat, k.remoteJidAlt].find((j) => j && isPnUser(j));
  const numero = pn ? jidNormalizedUser(pn).split("@")[0] : "";
  if (estado.modo === "abierto") return { quien: numero ? enmascarar(numero) : "contacto" };
  return PERMITIDOS.has(numero) ? { quien: enmascarar(numero) } : null;
}

async function atender(msg, quien) {
  const t0 = Date.now();
  const chat = msg.key.remoteJid;
  const evento = { chat: quien };
  try {
    if (enviadosPorElBot.has(msg.key.id)) return;
    const contenido = normalizeMessageContent(msg.message);
    let cuerpo;
    if (contenido?.audioMessage) {
      evento.tipo = "voz";
      const audio = await downloadMediaMessage(msg, "buffer", {}, { logger, reuploadRequest: sock.updateMediaMessage });
      cuerpo = { audio_base64: audio.toString("base64") };
    } else {
      const texto = textoDe(contenido);
      if (!texto) {
        evento.tipo = "otro";
        evento.resultado = "tipo no soportado";
        await enviar(chat, "Por ahora leo texto y notas de voz. Escríbame «menú» para ver qué puedo hacer.", msg);
        return;
      }
      evento.tipo = "texto";
      cuerpo = { texto };
    }

    await sock.sendPresenceUpdate("composing", chat).catch(() => {});
    const d = await preguntarAlWorker(cuerpo, chat);
    evento.accion = d.ruta?.accion;
    const prefijo = d.transcripcion ? "🎙️ _Entendí: «" + d.transcripcion + "»_\n\n" : "";
    const documentos = (d.adjuntos || []).filter((a) => a.tipo === "documento");
    if (documentos.length) {
      try {
        for (const [i, a] of documentos.entries()) await enviarDocumento(chat, a, i === 0 ? prefijo + d.respuesta : a.nombre, msg);
        evento.resultado = "contestado con " + documentos.length + " documento(s)";
      } catch (e) {
        // Si el archivo no baja, al menos va el enlace.
        await enviar(chat, prefijo + d.respuesta + "\n\n📎 " + documentos.map((a) => a.url).join("\n📎 "), msg);
        evento.resultado = "contestado con enlace (" + String(e.message || e).slice(0, 80) + ")";
      }
    } else {
      await enviar(chat, prefijo + d.respuesta, msg);
      evento.resultado = "contestado";
    }
  } catch (e) {
    evento.resultado = "error";
    evento.error = String(e?.message || e).slice(0, 200);
    try {
      await enviar(chat, /timeout|abort/i.test(evento.error)
        ? "⏳ Cloudflare tardó demasiado en contestar. Vuelva a pedírmelo en un momento."
        : "⚠️ No pude consultar el informe en Cloudflare. Inténtelo de nuevo en un momento.", msg);
    } catch { /* nada mas que hacer */ }
  } finally {
    await sock.sendPresenceUpdate("paused", chat).catch(() => {});
    evento.ms = Date.now() - t0;
    anotar(evento);
  }
}

async function conectar() {
  desvinculadoAMano = false;
  const { state, saveCreds } = await useMultiFileAuthState(SESION);
  let version;
  try {
    ({ version } = await fetchLatestBaileysVersion());
  } catch { /* si GitHub no responde, Baileys usa la version que trae */ }

  sock = makeWASocket({
    auth: state,
    version,
    logger,
    browser: Browsers.windows("Chrome"),
    markOnlineOnConnect: false,          // asi el celular sigue recibiendo notificaciones
    syncFullHistory: false,
    shouldSyncHistoryMessage: () => false, // no se baja el historial de chats
    getMessage: async (key) => cache.get(key.id),
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      intentos = 0; // si vence el QR no se castiga con espera: sale otro de una
      estado.conexion = "esperando_qr";
      estado.qr = await QRCode.toDataURL(qr, { margin: 1, width: 320 });
      console.log("\nEscanee este QR desde WhatsApp > Dispositivos vinculados (o abra " + PANEL + "):\n");
      console.log(await QRCode.toString(qr, { type: "terminal", small: true }));
      // Si arranco escondido (con Windows) y hay que escanear, el panel se abre solo.
      if (!panelAbierto) { panelAbierto = true; abrirPanel(); }
    }
    if (connection === "open") {
      intentos = 0;
      misJids = new Set([sock.user?.id, sock.user?.lid].filter(Boolean).map(jidNormalizedUser));
      miChat = jidNormalizedUser(sock.user?.id || "");
      estado.conexion = "conectado";
      estado.qr = null;
      estado.yo = enmascarar(miChat.split("@")[0]);
      estado.desde = new Date().toISOString();
      anotar({ tipo: "conexion", resultado: "conectado como " + estado.yo });
      console.log("Listo. Escríbase a sí mismo en WhatsApp («Mensaje para mí») y el informe le contesta.");
      if (!yaSaludo) avisarme("Puente conectado. " + describirModo() + "\n\nÓrdenes: «bot off» · «bot yo» · «bot abierto» · «bot abierto 5» · «bot estado»" +
        (CON_AGENDA ? "\n\n⏰ Le aviso aquí 30 min antes de cada cita de la agenda." : ""));
      yaSaludo = true;
      setTimeout(revisarRecordatorios, 5000);
    }
    if (connection === "close") {
      const codigo = lastDisconnect?.error?.output?.statusCode;
      estado.qr = null;
      if (desvinculadoAMano) {
        estado.conexion = "desvinculado";
        fs.rmSync(SESION, { recursive: true, force: true });
      } else if (codigo === DisconnectReason.loggedOut) {
        // Lo desvincularon desde el celular: la sesion guardada ya no sirve.
        estado.conexion = "desvinculado";
        anotar({ tipo: "conexion", resultado: "desvinculado desde el celular; para volver: botón «Vincular de nuevo»" });
        fs.rmSync(SESION, { recursive: true, force: true });
      } else if (codigo === DisconnectReason.connectionReplaced) {
        estado.conexion = "reemplazada";
        anotar({ tipo: "conexion", resultado: "otro puente abrió la misma sesión; este se detiene" });
      } else {
        estado.conexion = "reconectando";
        const espera = codigo === DisconnectReason.restartRequired ? 500 : Math.min(30000, 2000 * 2 ** intentos++);
        anotar({ tipo: "conexion", resultado: "se cayó (código " + (codigo ?? "?") + "); reintento en " + Math.round(espera / 1000) + " s" });
        setTimeout(conectar, espera);
      }
    }
  });

  sock.ev.on("messages.upsert", ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || !msg.key?.id || vistos.has(msg.key.id)) continue;
      if (Number(msg.messageTimestamp || 0) < ARRANQUE - 30) continue; // nada de mensajes viejos
      const c = clasificar(msg);
      if (!c) continue;
      recordar(vistos, msg.key.id);
      if (c.orden) {
        // Las ordenes no hacen fila detras de un analisis largo: van de una.
        if (c.orden.modo) cambiarModo(c.orden.modo, "WhatsApp", c.orden.minutos);
        enviar(msg.key.remoteJid, describirModo(), msg).catch(() => {});
        continue;
      }
      cola = cola.then(() => atender(msg, c.quien)).catch(() => {});
    }
  });
}

// ---------------------------------------------------------------------------
// RECORDATORIOS: cada minuto se le pregunta al Worker que citas empiezan en
// los proximos 30 minutos. El aviso llega al chat consigo mismo. El Worker
// marca cada cita como avisada, asi que no se repite. En modo apagado no avisa.
// ---------------------------------------------------------------------------
const URL_RECORDATORIOS = new URL("/api/recordatorios?minutos=30", CONFIG.worker).href;

let sinAgenda = false; // el cerebro dijo que no tiene agenda: no se vuelve a preguntar

async function revisarRecordatorios() {
  if (!CON_AGENDA || sinAgenda || estado.conexion !== "conectado" || estado.modo === "apagado") return;
  try {
    const r = await fetch(URL_RECORDATORIOS, { headers: { "x-clave": CONFIG.clave_puente }, signal: AbortSignal.timeout(20000) });
    if (r.status === 404) { sinAgenda = true; return; }
    const d = await r.json();
    if (d.agenda === false) { sinAgenda = true; return; }
    if (!d.ok) {
      anotar({ tipo: "recordatorio", resultado: "error", error: d.error });
      return;
    }
    for (const x of d.recordatorios || []) {
      await avisarme(x.texto);
      anotar({ chat: "yo", tipo: "recordatorio", accion: "cita #" + x.id, resultado: "enviado" });
    }
  } catch { /* un minuto sin internet: se intenta en el siguiente */ }
}
setInterval(revisarRecordatorios, 60000);

// ---------------------------------------------------------------------------
// PAGINA LOCAL: el QR, el estado y los botones. Solo escucha en este
// computador (127.0.0.1): el QR da acceso a su WhatsApp. Los botones exigen
// la cabecera x-puente para que otra pagina web no pueda accionarlos.
// ---------------------------------------------------------------------------
const PAGINA = fs.readFileSync(path.join(AQUI, "pagina.html"), "utf8");
const HOSTS = new Set(["localhost:" + CONFIG.puerto, "127.0.0.1:" + CONFIG.puerto]);

async function accion(nombre, minutos) {
  if (["apagado", "solo_yo", "abierto"].includes(nombre)) {
    cambiarModo(nombre, "la página", minutos);
    await avisarme(describirModo());
  } else if (nombre === "desvincular") {
    // Cierra la sesion en WhatsApp: desaparece de "Dispositivos vinculados".
    desvinculadoAMano = true;
    anotar({ tipo: "conexion", resultado: "desvinculado desde la página" });
    await avisarme("🔌 Me desvinculé de este WhatsApp. Para volver hay que escanear el QR otra vez.");
    await sock?.logout().catch(() => {});
    estado.conexion = "desvinculado";
  } else if (nombre === "vincular") {
    if (estado.conexion === "desvinculado") conectar();
  } else if (nombre === "detener") {
    await avisarme("⏹️ Puente detenido. Su WhatsApp sigue normal; nadie le contesta por usted.");
    console.log("\nPuente detenido desde la página. La sesión queda guardada.");
    setTimeout(() => process.exit(0), 300);
  } else {
    return false;
  }
  return true;
}

http
  .createServer(async (req, res) => {
    if (!HOSTS.has(req.headers.host)) {
      res.writeHead(403).end();
      return;
    }
    const url = new URL(req.url, "http://localhost");
    if (url.pathname === "/estado") {
      res.writeHead(200, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
      res.end(JSON.stringify({ ...estado, worker: CONFIG.worker, permitidos: PERMITIDOS.size, minutosAbierto: MINUTOS_ABIERTO, recordatorios: CON_AGENDA && !sinAgenda }));
      return;
    }
    if (url.pathname.startsWith("/accion/") && req.method === "POST") {
      if (req.headers["x-puente"] !== "1") {
        res.writeHead(403).end();
        return;
      }
      const ok = await accion(url.pathname.slice(8), url.searchParams.get("min"));
      res.writeHead(ok ? 200 : 404, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok, modo: estado.modo, conexion: estado.conexion }));
      return;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(PAGINA);
  })
  .on("error", (e) => {
    console.error(e.code === "EADDRINUSE"
      ? "El puerto " + CONFIG.puerto + " está ocupado por otro programa. Cámbielo en config.json (y en los .bat)."
      : "No pude abrir la página local: " + e.message);
    process.exit(1);
  })
  .listen(CONFIG.puerto, "127.0.0.1", () => {
    console.log("Puente WhatsApp ↔ Cloudflare · página de estado en " + PANEL);
    console.log("Modo al arrancar: " + estado.modo + (fs.existsSync(MODO_GUARDADO) ? " (el último en que se dejó)" : ""));
    if (!process.argv.includes("--sin-navegador")) { panelAbierto = true; abrirPanel(); }
  });

process.on("SIGINT", () => {
  console.log("\nPuente detenido. La sesión queda guardada: la próxima vez no pide QR.");
  process.exit(0);
});

conectar();
