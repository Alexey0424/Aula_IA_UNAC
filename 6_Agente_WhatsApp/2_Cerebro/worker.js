/* ===========================================================================
   CEREBRO DEL AGENTE DE WHATSAPP · plantilla del aula
   Diplomado en Inteligencia Artificial · UNAC · Clase 12
   ===========================================================================
   Lo llama el PUENTE: el programa del computador que esta vinculado a
   WhatsApp como dispositivo (carpeta 1_Puente). Por cada mensaje:

     1. recibe el texto, o la nota de voz en base64 (Whisper la vuelve texto)
     2. LEE EL INFORME publicado (INFORME_URL): lo abre en un navegador de
        Cloudflare (Browser Rendering), toma lo que se ve, el texto de las
        pestanas ocultas y los datos que traiga el codigo de la pagina, y lo
        guarda 15 min en KV. Asi sirve para CUALQUIER informe, sin tocarlo.
     3. un LLM de Workers AI contesta con base en ese contenido, o pide una
        TOOL (el modelo no ejecuta nada: dice cual quiere y el Worker la corre)
     4. devuelve la respuesta, y el PDF del informe si se lo pidieron

   NIVEL 1 (todos):    preguntas sobre el informe + enviar_informe_pdf
   NIVEL 2 (opcional): si hay una base D1 con binding DB -> agenda de citas,
                       notas de clientes y recordatorios 30 min antes.

   QUE SE AJUSTA POR ESTUDIANTE: solo wrangler.toml (nombre, INFORME_URL,
   EMPRESA, CONTEXTO_EXTRA y los ids). El codigo es el mismo para todos.
   Secreto obligatorio: CLAVE_PUENTE (la misma de config.json del puente).
   =========================================================================== */
import puppeteer from "@cloudflare/puppeteer";

// El primero decide las tools; el segundo es de respaldo si el primero falla.
const MODELOS = ["@cf/meta/llama-3.3-70b-instruct-fp8-fast", "@cf/meta/llama-4-scout-17b-16e-instruct"];
const MODELO_VOZ = "@cf/openai/whisper-large-v3-turbo";
// Caracteres del informe que se le pasan al modelo EN CADA MENSAJE. Es lo que mas
// gasta: ~18.000 caracteres son ~5.000 tokens, unos 150 neurons por mensaje con
// el modelo de 70B, de los 10.000 diarios gratis. Subirlo da mas detalle y menos mensajes.
const MAX_CONTEXTO = 18000;
const VIGENCIA_TEXTO = 900;   // s: el informe se vuelve a leer cada 15 min
const VIGENCIA_PDF = 3600000; // ms: el PDF se rehace cada hora (o si cambia la agenda)

// ---------------------------------------------------------------------------
// UTILIDADES
// ---------------------------------------------------------------------------
const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "content-type" };
const json = (o, s, extra) =>
  new Response(JSON.stringify(o, null, 2), {
    status: s || 200,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...(extra || {}) },
  });
const sinTildes = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const empresa = (env) => env.EMPRESA || "la empresa";
const nivel = (env) => (env.DB ? 2 : 1);

async function huella(texto) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(texto)));
  return [...new Uint8Array(h)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------------------------------------------------------------------------
// LA HORA DE COLOMBIA (UTC-5 todo el ano). El modelo no sabe que dia es hoy:
// hay que decirselo en cada mensaje, o "manana" no significa nada.
// ---------------------------------------------------------------------------
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function ahoraCol(desplazamientoMin = 0) {
  const d = new Date(Date.now() - 5 * 3600 * 1000 + desplazamientoMin * 60000);
  return { iso: d.toISOString().slice(0, 10), hora: d.toISOString().slice(11, 16), seg: d.toISOString().slice(11, 19) };
}
const fechaDe = (iso) => new Date(iso + "T12:00:00Z");
const sumarDias = (iso, n) => new Date(fechaDe(iso).getTime() + n * 86400000).toISOString().slice(0, 10);
const fechaLarga = (iso) => { const f = fechaDe(iso); return DIAS[f.getUTCDay()] + " " + f.getUTCDate() + " de " + MESES[f.getUTCMonth()]; };
const hora12 = (h) => { const [a, b] = h.split(":"); const n = +a; return (n % 12 || 12) + ":" + b + (n < 12 ? " a. m." : " p. m."); };
const minutos = (h) => { const [a, b] = h.split(":"); return +a * 60 + +b; };
const esFecha = (s) => /^\d{4}-\d{2}-\d{2}$/.test(s || "") && !isNaN(fechaDe(s)) && fechaDe(s).toISOString().slice(0, 10) === s;

function normalizarHora(h) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(h || "").trim());
  if (!m || +m[1] > 23 || +m[2] > 59) return null;
  return m[1].padStart(2, "0") + ":" + m[2];
}

async function transcribir(env, audioBase64) {
  const r = await env.AI.run(MODELO_VOZ, { audio: audioBase64, language: "es" });
  return ((r && r.text) || "").trim();
}

/* ===========================================================================
   LEER EL INFORME. Se abre UNA vez el navegador y se saca todo de una:
   el texto (para el modelo) y el PDF (para mandarlo). El plan gratuito deja
   abrir un navegador cada 20 s y 10 min de navegador al dia, por eso se guarda.
   =========================================================================== */
const limpiar = (t) => String(t || "").replace(/[ \t ]+/g, " ").replace(/\s*\n\s*/g, "\n").replace(/\n{3,}/g, "\n\n").trim();

// Arma lo que lee el modelo: lo visible primero; luego lo que esta en pestanas o
// filtros que no se ven; y al final los datos que vienen en el codigo (graficas).
function armarContexto({ visible, todo, scripts }) {
  const v = limpiar(visible);
  const t = limpiar(todo);
  let ctx = v;
  if (t.length > v.length * 1.3) ctx += "\n\n[CONTENIDO DE LA PÁGINA QUE NO ESTÁ A LA VISTA: pestañas, filtros u otras secciones]\n" + t;
  const conDatos = (scripts || [])
    .map((s) => String(s || "").trim())
    .filter((s) => (s.match(/\d/g) || []).length >= 20)
    .sort((a, b) => (b.match(/\d/g) || []).length - (a.match(/\d/g) || []).length);
  let datos = "";
  for (const s of conDatos) {
    if (datos.length + s.length > 6000) { datos += s.slice(0, Math.max(0, 6000 - datos.length)); break; }
    datos += s + "\n";
  }
  const espacio = MAX_CONTEXTO - (datos ? datos.length + 120 : 0);
  ctx = ctx.slice(0, Math.max(10000, espacio));
  if (datos) ctx += "\n\n[DATOS QUE TRAE EL CÓDIGO DE LA PÁGINA (por ejemplo, los de las gráficas)]\n" + datos;
  return ctx.slice(0, MAX_CONTEXTO);
}

async function renderizar(env) {
  const navegador = await puppeteer.launch(env.NAVEGADOR);
  try {
    const page = await navegador.newPage();
    await page.setViewport({ width: 1280, height: 900 });
    await page.goto(env.INFORME_URL, { waitUntil: "networkidle0", timeout: 30000 });
    await new Promise((r) => setTimeout(r, 1500)); // las graficas animadas terminan de pintarse
    const titulo = await page.title();
    const piezas = await page.evaluate(() => {
      const clon = document.body.cloneNode(true);
      clon.querySelectorAll("script,style,noscript,template").forEach((n) => n.remove());
      return {
        visible: document.body.innerText,
        todo: clon.textContent,
        scripts: [...document.querySelectorAll("script:not([src])")].map((s) => s.textContent),
      };
    });
    // El PDF sale tal como se ve en pantalla, en horizontal (los tableros son anchos).
    await page.emulateMediaType("screen");
    const pdf = await page.pdf({ format: "A4", landscape: true, printBackground: true, margin: { top: "8mm", bottom: "8mm", left: "8mm", right: "8mm" } });
    return { titulo, contexto: armarContexto(piezas), pdf };
  } finally {
    await navegador.close();
  }
}

// Respaldo sin navegador: se baja el HTML y se le quitan las etiquetas.
async function leerSinNavegador(env) {
  const r = await fetch(env.INFORME_URL, { headers: { "user-agent": "cerebro-whatsapp" } });
  if (!r.ok) throw new Error("El informe respondió HTTP " + r.status + " en " + env.INFORME_URL);
  const html = await r.text();
  const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
  const titulo = (/<title[^>]*>([\s\S]*?)<\/title>/i.exec(html) || [])[1] || "";
  const texto = html
    .replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<!--[\s\S]*?-->/gi, " ")
    .replace(/<(br|\/p|\/div|\/li|\/tr|\/h\d|\/section|\/td|\/th)[^>]*>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
  return { titulo: titulo.trim(), contexto: armarContexto({ visible: texto, todo: "", scripts }), via: "html (sin navegador)" };
}

async function huellaAgenda(env) {
  if (!env.DB) return "";
  try {
    const f = await env.DB.prepare("SELECT COUNT(*) AS n, COALESCE(MAX(id), 0) AS m, SUM(estado = 'cancelada') AS c FROM citas").first();
    return f.n + "-" + f.m + "-" + f.c;
  } catch (e) { return ""; }
}

// Devuelve { titulo, contexto, via, leido, pdf: {v, kb} | null, errorNavegador? }
async function obtenerInforme(env, { necesitoPdf = false, fresco = false } = {}) {
  if (!env.INFORME_URL) throw new Error("Falta la variable INFORME_URL en wrangler.toml.");
  const guardado = fresco ? null : await env.ESTADO.get("informe:contexto", "json");
  const agenda = await huellaAgenda(env);
  let meta = await env.ESTADO.get("informe:pdf:ultimo", "json");
  const pdfVigente = !fresco && meta && Date.now() - meta.generado < VIGENCIA_PDF && meta.agenda === agenda;
  if (guardado && (!necesitoPdf || pdfVigente)) return { ...guardado, pdf: pdfVigente ? meta : null };

  const a = ahoraCol();
  try {
    const r = await renderizar(env);
    const v = Date.now().toString(36);
    await env.ESTADO.put("informe:pdf:" + v, r.pdf, { expirationTtl: 86400 });
    meta = { v, generado: Date.now(), agenda, kb: Math.round(r.pdf.byteLength / 1024) };
    await env.ESTADO.put("informe:pdf:ultimo", JSON.stringify(meta), { expirationTtl: 86400 });
    const c = { titulo: r.titulo, contexto: r.contexto, via: "navegador", leido: a.iso + " " + a.hora };
    await env.ESTADO.put("informe:contexto", JSON.stringify(c), { expirationTtl: VIGENCIA_TEXTO });
    return { ...c, pdf: meta };
  } catch (e) {
    const errorNavegador = String(e && e.message ? e.message : e).slice(0, 200);
    if (guardado) return { ...guardado, pdf: pdfVigente ? meta : null, errorNavegador };
    const c = { ...(await leerSinNavegador(env)), leido: a.iso + " " + a.hora };
    await env.ESTADO.put("informe:contexto", JSON.stringify(c), { expirationTtl: 300 });
    return { ...c, pdf: pdfVigente ? meta : null, errorNavegador };
  }
}

/* ===========================================================================
   NIVEL 1: EL PDF DEL INFORME
   =========================================================================== */
const nombreArchivo = (env) =>
  "Informe_" + (sinTildes(empresa(env)).replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "gestion") + "_" + ahoraCol().iso + ".pdf";

async function enviarInformePdf(env, a, ctx) {
  const inf = await obtenerInforme(env, { necesitoPdf: true });
  if (!inf.pdf) {
    return {
      texto: /429|rate|limit|too many/i.test(inf.errorNavegador || "")
        ? "⏳ El generador de PDF de Cloudflare está ocupado (límite del plan gratuito). Pídamelo otra vez en un minuto."
        : "⚠️ No pude generar el PDF ahora" + (inf.errorNavegador ? ": " + inf.errorNavegador : ".") + "\nAquí está el informe en línea: " + env.INFORME_URL,
    };
  }
  return {
    ref: "PDF " + inf.pdf.kb + " KB",
    texto: "📄 *" + (inf.titulo || "Informe de gestión") + "*\n" + empresa(env) + " · " + inf.pdf.kb + " KB",
    adjuntos: [{ tipo: "documento", url: ctx.origen + "/informe.pdf?v=" + inf.pdf.v, nombre: nombreArchivo(env), mimetype: "application/pdf" }],
  };
}

/* ===========================================================================
   NIVEL 2: LA AGENDA Y LOS CLIENTES (solo si hay base D1 con binding DB)
   =========================================================================== */
const coincide = (fila, termino) => {
  const t = sinTildes(termino).trim();
  return !!t && (sinTildes(fila.cliente).includes(t) || sinTildes(fila.empresa).includes(t) ||
    t.split(/\s+/).filter((p) => p.length > 2).every((p) => sinTildes(fila.cliente + " " + (fila.empresa || "")).includes(p)));
};
const quien = (c) => c.cliente + (c.empresa ? " · " + c.empresa : "");
const lineaCita = (c) => "• " + hora12(c.hora) + " — *" + quien(c) + "*" + (c.asunto ? ": " + c.asunto : "") + (c.lugar ? " _(" + c.lugar + ")_" : "") + " _#" + c.id + "_";

async function proximasCitas(env) {
  const r = await env.DB.prepare("SELECT * FROM citas WHERE estado = 'programada' AND fecha >= ?1 ORDER BY fecha, hora LIMIT 300").bind(ahoraCol().iso).all();
  return r.results || [];
}

// El modelo a veces corta un nombre justo antes de una tilde ("Juli" por "Julián").
// Si lo que llego es el comienzo de un cliente conocido, se completa.
async function nombreConocido(env, cliente) {
  const t = sinTildes(cliente).trim();
  if (!t) return cliente;
  const r = await env.DB.prepare("SELECT DISTINCT cliente FROM citas UNION SELECT DISTINCT cliente FROM notas").all();
  const nombres = (r.results || []).map((x) => x.cliente);
  if (nombres.some((n) => sinTildes(n) === t)) return cliente;
  const candidatos = [...new Set(nombres.filter((n) => sinTildes(n).startsWith(t) && /[a-z ]/.test(sinTildes(n).charAt(t.length))))];
  return candidatos.length === 1 ? candidatos[0] : cliente;
}

// Si dijo "Julian" sin la empresa, se busca en lo que ya se sabe de el.
async function empresaConocida(env, cliente) {
  const t = sinTildes(cliente);
  if (!t) return null;
  const r = await env.DB.prepare(
    "SELECT cliente, empresa FROM citas WHERE empresa IS NOT NULL UNION ALL SELECT cliente, empresa FROM notas WHERE empresa IS NOT NULL"
  ).all();
  const f = (r.results || []).find((x) => sinTildes(x.cliente) === t || sinTildes(x.cliente).split(" ")[0] === t);
  return f ? f.empresa : null;
}

// El modelo tiende a INVENTAR la hora cuando no se la dicen ("el lunes" -> 10:00).
// Las instrucciones no bastan: aqui se verifica que el usuario si haya dicho
// un dia y una hora, en este mensaje o en el anterior si quedo una pregunta pendiente.
const mencionaHora = (t) =>
  /\ba\s+las?\b|\d{1,2}:\d{2}|\b\d{1,2}\s*(am|pm|a\.\s?m\.?|p\.\s?m\.?|h|hrs?|horas)\b|mediod[ií]a|medianoche|en punto|de la (mañana|manana|tarde|noche)/i.test(t);
const mencionaFecha = (t) =>
  /\bhoy\b|mañana|manana|pasado|lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo|\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)|\bel\s+\d{1,2}\b|\d{1,2}\/\d{1,2}|semana|pr[oó]xim/i.test(t);

// El modelo se equivoca de dia de la semana ("el martes" -> lunes 19, medido el
// 15-oct-2026). Si el usuario dijo hoy, manana, pasado manana o un dia de la
// semana, la fecha se calcula aqui y manda sobre la del modelo.
const NOMBRES_DIA = ["domingo", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado"];
function fechaDicha(texto, fechaModelo) {
  const s = sinTildes(texto).replace(/(de|en|por) la manana/g, " "); // "a las 10 de la manana" no es "manana"
  const hoy = ahoraCol().iso;
  const dichos = NOMBRES_DIA.filter((d) => new RegExp("\\b" + d + "\\b").test(s));
  if (dichos.length === 1) {
    const objetivo = NOMBRES_DIA.indexOf(dichos[0]);
    let cercana = null;
    for (let i = 1; i <= 7 && !cercana; i++) if (fechaDe(sumarDias(hoy, i)).getUTCDay() === objetivo) cercana = sumarDias(hoy, i);
    if (/proxima semana|semana que viene/.test(s)) return sumarDias(cercana, 7);
    // "el martes 27": si el modelo puso ese mismo dia de la semana en las proximas dos semanas, se le cree.
    const mismoDia = esFecha(fechaModelo) && fechaDe(fechaModelo).getUTCDay() === objetivo && fechaModelo > hoy && fechaModelo <= sumarDias(hoy, 14);
    return mismoDia ? fechaModelo : cercana;
  }
  if (dichos.length) return fechaModelo;
  if (/pasado\s+manana/.test(s)) return sumarDias(hoy, 2);
  if (/\bmanana\b/.test(s)) return sumarDias(hoy, 1);
  if (/\bhoy\b/.test(s)) return hoy;
  return fechaModelo;
}

// El modelo a veces cambia el nombre ("Julian", "Julién" por "Julián"). Si en lo
// que dijo el usuario hay un nombre igual o casi igual (una letra de diferencia
// por cada cinco), se usa tal como lo escribio el.
function distancia(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
function comoLoDijo(nombre, texto) {
  const n = String(nombre || "").trim();
  if (!n) return n;
  const palabras = String(texto || "").split(/\s+/).map((p) => p.replace(/^[^\p{L}\d]+|[^\p{L}\d]+$/gu, ""));
  const k = n.split(/\s+/).length;
  let mejor = null, menor = Math.floor(sinTildes(n).length / 5);
  for (let i = 0; i + k <= palabras.length; i++) {
    const trozo = palabras.slice(i, i + k).join(" ");
    const dd = distancia(sinTildes(trozo), sinTildes(n));
    if (dd === 0 || (dd <= menor && (!mejor || dd < mejor.dd))) mejor = { trozo, dd };
    if (dd === 0) break;
  }
  return mejor ? mejor.trozo.charAt(0).toUpperCase() + mejor.trozo.slice(1) : n;
}

async function agendarCita(env, a, ctx) {
  // Si la cita quedo a medias ("¿a que hora?"), lo que ya se sabia se completa
  // aqui: con la respuesta corta ("a las 3") el modelo a veces olvida con quien
  // era, o pone de cliente a la empresa del informe.
  const pend = ctx.pendiente ? ctx.estado.pend : null;
  if (pend) {
    if (pend.cliente && sinTildes(a.cliente) === sinTildes(empresa(env))) a.cliente = "";
    for (const k of Object.keys(pend)) if (!a[k] && pend[k]) a[k] = pend[k];
  }
  const ahora = ahoraCol();
  const fecha = fechaDicha(ctx.recientes || ctx.texto, String(a.fecha || "").trim());
  const hora = normalizarHora(a.hora);
  const cliente = await nombreConocido(env, comoLoDijo(a.cliente, ctx.recientes || ctx.texto));
  a.empresa = comoLoDijo(a.empresa, ctx.recientes || ctx.texto);
  const dicho = ctx.recientes || ctx.texto;
  const aMedias = async (texto) => {
    ctx.estado.pend = { ...a, fecha: esFecha(fecha) ? fecha : a.fecha, cliente };
    return { pregunta: true, texto };
  };
  if (cliente && !mencionaFecha(dicho)) return aMedias("📅 ¿Para qué *día* agendo la cita con " + cliente + "?");
  if (cliente && !mencionaHora(dicho)) {
    return aMedias("📅 ¿A qué *hora* agendo la cita con " + cliente + (esFecha(fecha) ? " el " + fechaLarga(fecha) : "") + "?");
  }
  if (!esFecha(fecha) || !hora || !cliente) {
    return aMedias("📅 Para agendar necesito la *fecha*, la *hora* y *con quién* es la cita. ¿Me los confirma?");
  }
  ctx.estado.pend = null;
  if (fecha < ahora.iso || (fecha === ahora.iso && hora <= ahora.hora)) {
    return { texto: "📅 Esa fecha y hora ya pasaron (" + fechaLarga(fecha) + ", " + hora12(hora) + "). ¿Para cuándo la agendo?" };
  }
  const emp = String(a.empresa || "").trim() || (await empresaConocida(env, cliente));
  const asunto = String(a.asunto || "").trim() || null;
  const lugar = String(a.lugar || "").trim() || null;
  const dur = Math.min(480, Math.max(15, parseInt(a.duracion_min, 10) || 60));
  const mismoDia = (await env.DB.prepare("SELECT * FROM citas WHERE estado = 'programada' AND fecha = ?1").bind(fecha).all()).results || [];
  const choques = mismoDia.filter((c) => minutos(hora) < minutos(c.hora) + c.duracion_min && minutos(c.hora) < minutos(hora) + dur);
  const r = await env.DB.prepare(
    "INSERT INTO citas (fecha, hora, duracion_min, cliente, empresa, asunto, lugar, origen, creada) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)"
  ).bind(fecha, hora, dur, cliente, emp, asunto, lugar, ctx.origenMsg, ahora.iso + " " + ahora.seg).run();
  return {
    ref: "cita #" + r.meta.last_row_id,
    texto: [
      "✅ *Cita agendada* _#" + r.meta.last_row_id + "_",
      "📅 " + fechaLarga(fecha) + " · " + hora12(hora) + " (" + dur + " min)",
      "👤 " + cliente + (emp ? " · " + emp : ""),
      ...(asunto ? ["📝 " + asunto] : []),
      ...(lugar ? ["📍 " + lugar] : []),
      ...(choques.length ? ["", "⚠️ Ojo: a esa hora ya tenía " + choques.map((c) => hora12(c.hora) + " con " + quien(c)).join(" y ") + "."] : []),
      "",
      "_Le aviso 30 min antes._",
    ].join("\n"),
  };
}

async function verAgenda(env, a) {
  const hoy = ahoraCol().iso;
  let desde = esFecha(a.desde) ? a.desde : hoy;
  let hasta = esFecha(a.hasta) ? a.hasta : sumarDias(desde, 6);
  if (hasta < desde) [desde, hasta] = [hasta, desde];
  if (fechaDe(hasta) - fechaDe(desde) > 62 * 86400000) hasta = sumarDias(desde, 62);
  const r = await env.DB.prepare("SELECT * FROM citas WHERE estado = 'programada' AND fecha BETWEEN ?1 AND ?2 ORDER BY fecha, hora").bind(desde, hasta).all();
  const citas = r.results || [];
  const rango = desde === hasta ? fechaLarga(desde) : "del " + fechaLarga(desde) + " al " + fechaLarga(hasta);
  if (!citas.length) return "🗓️ No tiene citas " + (desde === hasta ? "el " : "") + rango + ".";
  const porDia = {};
  citas.forEach((c) => (porDia[c.fecha] = porDia[c.fecha] || []).push(c));
  return "🗓️ *Agenda " + rango + "* (" + citas.length + ")\n\n" +
    Object.keys(porDia).map((f) => "*" + fechaLarga(f) + (f === hoy ? " (hoy)" : "") + "*\n" + porDia[f].map(lineaCita).join("\n")).join("\n\n");
}

async function cancelarCita(env, a) {
  let citas = await proximasCitas(env);
  const id = parseInt(a.id, 10);
  if (id) citas = citas.filter((c) => c.id === id);
  if (esFecha(a.fecha)) citas = citas.filter((c) => c.fecha === a.fecha);
  const termino = String(a.cliente || a.empresa || "").trim();
  if (termino) citas = citas.filter((c) => coincide(c, termino));
  if (!id && !termino && !esFecha(a.fecha)) return "🗑️ ¿Cuál cita cancelo? Dígame con quién es o de qué fecha.";
  if (!citas.length) return "🗑️ No encontré una cita próxima" + (termino ? " con *" + termino + "*" : "") + (esFecha(a.fecha) ? " el " + fechaLarga(a.fecha) : "") + ". Escriba «mi agenda» para verlas.";
  if (citas.length > 1) {
    return "🗑️ Encontré " + citas.length + " citas. ¿Cuál cancelo? Dígame el número:\n\n" +
      citas.slice(0, 8).map((c) => "• _#" + c.id + "_ " + fechaLarga(c.fecha) + " · " + hora12(c.hora) + " — " + quien(c)).join("\n");
  }
  const c = citas[0];
  await env.DB.prepare("UPDATE citas SET estado = 'cancelada' WHERE id = ?1").bind(c.id).run();
  return "🗑️ *Cita cancelada* _#" + c.id + "_\n" + fechaLarga(c.fecha) + " · " + hora12(c.hora) + " — " + quien(c) + (c.asunto ? "\n_" + c.asunto + "_" : "");
}

async function guardarNota(env, a, ctx) {
  const cliente = await nombreConocido(env, comoLoDijo(a.cliente, ctx.recientes || ctx.texto));
  a.empresa = comoLoDijo(a.empresa, ctx.recientes || ctx.texto);
  const nota = String(a.nota || "").trim();
  if (!cliente || !nota) return "📝 ¿Sobre qué cliente es la nota y qué anoto?";
  const emp = String(a.empresa || "").trim() || (await empresaConocida(env, cliente));
  const ahora = ahoraCol();
  await env.DB.prepare("INSERT INTO notas (cliente, empresa, nota, origen, creada) VALUES (?1, ?2, ?3, ?4, ?5)")
    .bind(cliente, emp, nota, ctx.origenMsg, ahora.iso + " " + ahora.seg).run();
  return "📝 *Anotado* en la ficha de " + cliente + (emp ? " · " + emp : "") + ":\n«" + nota + "»";
}

async function fichaCliente(env, a) {
  const termino = String(a.cliente || a.empresa || "").trim();
  if (!termino) return "🗂️ ¿De qué cliente quiere la ficha?";
  const [n, c] = await Promise.all([
    env.DB.prepare("SELECT * FROM notas ORDER BY creada DESC, id DESC LIMIT 500").all(),
    env.DB.prepare("SELECT * FROM citas ORDER BY fecha DESC, hora DESC LIMIT 500").all(),
  ]);
  const notas = (n.results || []).filter((x) => coincide(x, termino));
  const citas = (c.results || []).filter((x) => coincide(x, termino));
  if (!notas.length && !citas.length) return "🗂️ No tengo nada guardado sobre *" + termino + "* todavía. Puede dictarme una nota: «anota que…».";
  const hoy = ahoraCol().iso;
  const titulo = notas[0] || citas[0];
  const prox = citas.filter((x) => x.estado === "programada" && x.fecha >= hoy).reverse();
  const pasadas = citas.filter((x) => !(x.estado === "programada" && x.fecha >= hoy)).slice(0, 4);
  return [
    "🗂️ *Ficha: " + quien(titulo) + "*",
    ...(notas.length ? ["", "*Notas*", ...notas.slice(0, 6).map((x) => "• _" + fechaLarga(String(x.creada).slice(0, 10)) + "_ — " + x.nota)] : []),
    ...(prox.length ? ["", "*Próximas citas*", ...prox.map((x) => "• " + fechaLarga(x.fecha) + " · " + hora12(x.hora) + (x.asunto ? " — " + x.asunto : ""))] : []),
    ...(pasadas.length ? ["", "*Historial*", ...pasadas.map((x) => "• " + fechaLarga(x.fecha) + (x.asunto ? " — " + x.asunto : "") + (x.estado === "cancelada" ? " _(cancelada)_" : ""))] : []),
  ].join("\n");
}

// Recordatorios: el puente pregunta cada minuto que citas empiezan pronto.
// Cada cita se avisa una sola vez (columna "recordada").
async function recordatoriosPendientes(env, minutosAntes) {
  const ahora = ahoraCol(), limite = ahoraCol(minutosAntes);
  const r = await env.DB.prepare(
    "SELECT * FROM citas WHERE estado = 'programada' AND recordada = 0 AND (fecha || ' ' || hora) > ?1 AND (fecha || ' ' || hora) <= ?2 ORDER BY fecha, hora"
  ).bind(ahora.iso + " " + ahora.hora, limite.iso + " " + limite.hora).all();
  const citas = r.results || [];
  for (const c of citas) await env.DB.prepare("UPDATE citas SET recordada = 1 WHERE id = ?1").bind(c.id).run();
  return citas.map((c) => {
    const dias = Math.round((fechaDe(c.fecha) - fechaDe(ahora.iso)) / 86400000);
    const faltan = Math.max(1, dias * 1440 + minutos(c.hora) - minutos(ahora.hora));
    return {
      id: c.id,
      texto: "⏰ *Recordatorio:* en " + faltan + " min (" + hora12(c.hora) + ") tiene cita con *" + quien(c) + "*" +
        (c.asunto ? "\n📝 " + c.asunto : "") + (c.lugar ? "\n📍 " + c.lugar : ""),
    };
  });
}

/* ===========================================================================
   LAS TOOLS: lo que el modelo ve. Nombre, para que sirve y que datos pide.
   El modelo NO ejecuta nada: dice cual quiere y con que argumentos, y el
   Worker es el que la corre (EJECUTAR, mas abajo).
   =========================================================================== */
const texto = (descripcion) => ({ type: "string", description: descripcion });
const tool = (name, description, properties = {}, required = []) => ({
  type: "function",
  function: { name, description, parameters: { type: "object", properties, required } },
});

const TOOLS_NIVEL_1 = [
  tool("enviar_informe_pdf", "Envia el informe de gestion completo en PDF. Para 'mandame el informe', 'el PDF', 'el reporte completo', 'enviame el informe'."),
];
const TOOLS_NIVEL_2 = [
  tool("agendar_cita", "Crea una cita o reunion en la agenda.", {
    fecha: texto("Fecha en formato AAAA-MM-DD"),
    hora: texto("Hora de inicio en formato HH:MM de 24 horas"),
    cliente: texto("Nombre de la persona con quien es la cita"),
    empresa: texto("Empresa de esa persona, solo si la dijo"),
    asunto: texto("De que se trata la cita, si lo dijo"),
    duracion_min: { type: "integer", description: "Duracion en minutos; 60 si no la dijo" },
    lugar: texto("Donde es, si lo dijo"),
  }, ["fecha", "hora", "cliente"]),
  tool("ver_agenda", "Lista las citas de la agenda entre dos fechas. Para 'que tengo manana', 'mi agenda de la semana', 'que citas hay el lunes'.", {
    desde: texto("Fecha inicial AAAA-MM-DD"),
    hasta: texto("Fecha final AAAA-MM-DD (igual a desde si es un solo dia)"),
  }, ["desde", "hasta"]),
  tool("cancelar_cita", "Cancela una cita de la agenda. Se identifica por el cliente o la empresa, la fecha o el numero de la cita.", {
    cliente: texto("Nombre de la persona o de la empresa de la cita"),
    fecha: texto("Fecha de la cita AAAA-MM-DD, si la dijo"),
    id: { type: "integer", description: "Numero de la cita (#), si lo dijo" },
  }),
  tool("guardar_nota", "Guarda una nota en la ficha de un cliente. Para 'anota que...', 'apunta que...', 'deja registrado que...'.", {
    cliente: texto("Nombre de la persona"),
    empresa: texto("Empresa de esa persona, solo si la dijo"),
    nota: texto("Lo que hay que anotar, redactado en tercera persona y completo"),
  }, ["cliente", "nota"]),
  tool("ficha_cliente", "Muestra lo que se sabe de un cliente: notas guardadas y citas. Para 'que hemos hablado con...', 'la ficha de...'.",
    { cliente: texto("Nombre de la persona o de la empresa") }, ["cliente"]),
];
const herramientas = (env) => (env.DB ? [...TOOLS_NIVEL_1, ...TOOLS_NIVEL_2] : TOOLS_NIVEL_1);

// Lo que corre el Worker cuando el modelo pide una herramienta. Devuelve { texto, adjuntos?, ref?, pregunta? }.
const EJECUTAR = {
  enviar_informe_pdf: (env, a, ctx) => enviarInformePdf(env, a, ctx),
  agendar_cita: (env, a, ctx) => agendarCita(env, a, ctx),
  ver_agenda: async (env, a) => ({ texto: await verAgenda(env, a) }),
  cancelar_cita: async (env, a) => ({ texto: await cancelarCita(env, a) }),
  guardar_nota: async (env, a, ctx) => ({ texto: await guardarNota(env, a, ctx) }),
  ficha_cliente: async (env, a) => ({ texto: await fichaCliente(env, a) }),
};

function menu(env) {
  return [
    "Hola 👋 Soy el asistente de *" + empresa(env) + "*. Le contesto con lo que dice su informe de gestión.",
    "",
    "Pruebe, escribiendo o con nota de voz 🎙️:",
    "• «¿Cómo van los indicadores?»",
    "• «¿Qué es lo más preocupante del informe?»",
    "• «Mándame el informe en PDF»",
    ...(env.DB ? ["• «Agéndame una cita mañana a las 3 con Julián de Argos»", "• «¿Qué tengo esta semana?»", "• «Anota que Julián pidió 5 % de descuento»"] : []),
  ].join("\n");
}

function systemAgente(env, inf) {
  const a = ahoraCol();
  const cal = [];
  if (env.DB) {
    for (let i = 0; i < 14; i++) {
      const f = sumarDias(a.iso, i);
      cal.push("- " + (i === 0 ? "hoy, " : i === 1 ? "manana, " : "") + fechaLarga(f) + " = " + f);
    }
  }
  return [
    "Eres el asistente por WhatsApp de la gerencia de " + empresa(env) + ". Hablas en espanol de Colombia, con trato de usted.",
    "Contestas sobre el INFORME DE GESTION de la empresa, cuyo contenido esta al final de estas instrucciones.",
    "",
    "REGLAS:",
    "1. Usa SOLO las cifras y los hechos del informe. Si te preguntan un DATO que no esta en el informe,",
    "   dilo con claridad ('Ese dato no aparece en el informe') y no lo inventes.",
    "2. Si te piden una lectura (como vamos, que preocupa, que mejoro, que reviso primero), SI interpreta:",
    "   compara las cifras del informe entre periodos, sedes o areas y senala lo mejor y lo peor, con los numeros.",
    "3. Cita las cifras tal como aparecen en el informe, con el periodo al que corresponden. Decimales con coma.",
    "   Formato de WhatsApp: frases completas, *negrilla* solo para la cifra clave, listas con •, maximo 12 lineas.",
    "   Nada de titulos con #, ni tablas.",
    "4. Si piden el informe completo, el PDF o el reporte, llama la herramienta enviar_informe_pdf.",
    "5. El mensaje puede venir de una nota de voz transcrita con errores: interpretalo con sentido comun.",
    "6. Si solo conversa (gracias, listo, ok), contesta en una frase corta, sin herramientas.",
    ...(env.DB ? [
      "7. Agenda: fechas en AAAA-MM-DD y horas en HH:MM de 24 horas ('3 de la tarde' = 15:00).",
      "   Para agendar hacen falta fecha, hora y con quien. Si falta la HORA o la FECHA, NO la inventes:",
      "   pregunta en una frase corta y NO llames herramientas. 'esta semana' = desde hoy hasta el domingo;",
      "   'la proxima semana' = de lunes a domingo siguientes. El cliente es la persona que nombra el usuario,",
      "   nunca la empresa del informe.",
      "8. Si el usuario contesta algo corto ('a las 3', 'la de Argos', 'la #9'), completa con lo que se venia hablando.",
      "9. En el historial, las lineas 'Hecho: ...' son registros internos de herramientas que YA se ejecutaron.",
      "   NUNCA escribas una linea asi ni imites el resultado de una herramienta. Para agendar, cancelar, anotar",
      "   o enviar algo, SIEMPRE llama la herramienta: si no la llamas, no pasa nada.",
      "",
      "AHORA: " + fechaLarga(a.iso) + ", " + hora12(a.hora) + ", hora de Colombia. Calendario de referencia:",
      ...cal,
    ] : ["", "AHORA: " + fechaLarga(a.iso) + ", " + hora12(a.hora) + ", hora de Colombia."]),
    ...(env.CONTEXTO_EXTRA ? ["", "CONTEXTO DE LA EMPRESA (lo escribio la gerencia):", env.CONTEXTO_EXTRA] : []),
    "",
    "CONTENIDO DEL INFORME" + (inf.titulo ? " «" + inf.titulo + "»" : "") + " (leido el " + inf.leido + "):",
    "<<<",
    inf.contexto,
    ">>>",
  ].join("\n");
}

/* ===========================================================================
   MEMORIA CORTA: { turnos, pend }. turnos = los ultimos mensajes; pend = la cita
   que quedo a medias. En la memoria NO va la respuesta completa de una
   herramienta (el modelo aprende a copiarla y finge que la uso): va un
   registro corto "Hecho: ..." de que se hizo y con que datos.

   LA GUARDA EL PUENTE, no Cloudflare. KV tarda hasta un minuto en mostrar lo
   que se acaba de escribir (y recuerda los "no existe"): con una respuesta
   rapida ("a las 3") el agente no veia la pregunta anterior (medido el
   15-oct-2026). El puente la devuelve en cada mensaje. KV queda de respaldo
   para quien llame sin puente.
   =========================================================================== */
async function leerConversacion(env, conv, cuerpo) {
  if (cuerpo.memoria_en_puente) {
    const e = cuerpo.estado_conversacion || {};
    return { turnos: Array.isArray(e.turnos) ? e.turnos.slice(-8) : [], pend: e.pend || null, enPuente: true };
  }
  if (!conv) return { turnos: [], pend: null };
  try {
    const o = JSON.parse((await env.ESTADO.get("conv:" + conv)) || "{}");
    return { turnos: o.turnos || [], pend: o.pend || null };
  } catch (e) { return { turnos: [], pend: null }; }
}
async function guardarConversacion(env, conv, estado) {
  if (estado.enPuente || !conv) return;
  try { await env.ESTADO.put("conv:" + conv, JSON.stringify({ turnos: estado.turnos, pend: estado.pend }), { expirationTtl: 1800 }); } catch (e) { /* no tumba nada */ }
}

function leerLlamadas(r) {
  const msg = r && r.choices && r.choices[0] && r.choices[0].message;
  let crudas = (r && r.tool_calls) || (msg && msg.tool_calls) || [];
  let textoModelo = String((r && typeof r.response === "string" && r.response) || (msg && msg.content) || "").trim();
  // A veces el modelo ESCRIBE la llamada como texto ({"type":"function","function":{"name":...}})
  // en vez de hacerla (medido el 15-oct-2026). Eso nunca se le manda al usuario: se lee como llamada.
  if (!crudas.length && /^\{[\s\S]*"name"\s*:/.test(textoModelo)) {
    try {
      const o = JSON.parse(textoModelo);
      const f = o.function || o;
      crudas = [{ name: f.name, arguments: f.parameters || f.arguments || {} }];
    } catch (e) { /* JSON roto: se descarta */ }
    textoModelo = "";
  }
  const llamadas = crudas.map((c) => {
    const nombre = c.name || (c.function && c.function.name);
    let args = c.arguments !== undefined ? c.arguments : c.function && c.function.arguments;
    if (typeof args === "string") { try { args = JSON.parse(args || "{}"); } catch (e) { args = {}; } }
    // El modelo a veces llena lo que no sabe con "null" o "": eso es vacio.
    const limpios = {};
    for (const [k, v] of Object.entries(args || {})) {
      if (v === null || v === undefined || /^\s*(null|none|undefined|n\/a)?\s*$/i.test(String(v))) continue;
      limpios[k] = v;
    }
    return { nombre, args: limpios };
  }).filter((c) => EJECUTAR[c.nombre]);
  return { llamadas, textoModelo, neurons: r && r.usage && r.usage.neurons };
}

// El modelo escribe en markdown aunque se le pida lo contrario: se pasa a WhatsApp.
function formatoWhatsApp(t) {
  return String(t || "")
    .replace(/\*\*(.+?)\*\*/g, "*$1*")        // **negrilla** -> *negrilla*
    .replace(/^\s*#{1,6}\s*(.+)$/gm, "*$1*")  // # Titulo -> *Titulo*
    .replace(/^\s*[*-]\s+/gm, "• ")           // * item / - item -> • item
    .trim();
}

// ¿Pidio el documento? "pdf", o "informe/reporte" junto a mandar, enviar, pasar, dame...
function pidePdf(t) {
  const s = sinTildes(t);
  return /\bpdf\b/.test(s) || (/(informe|reporte|documento)/.test(s) && /(mand|envi|pasa|pasam|dame|compart|descarg|quiero|necesito|regal)/.test(s));
}

/* ===========================================================================
   EL AGENTE: de un texto a una respuesta.
   opciones: { conversacion, voz, origen, cuerpo }   (origen = direccion de este Worker)
   =========================================================================== */
async function pensar(env, textoUsuario, opciones = {}) {
  const ctx = { texto: textoUsuario, origen: opciones.origen, origenMsg: opciones.voz ? "voz" : "whatsapp" };
  const estado = await leerConversacion(env, opciones.conversacion, opciones.cuerpo || {});
  if (/^(hola|buenas|menu|menú|ayuda|inicio)[\s!.?]*$/i.test(textoUsuario.trim())) {
    return { ruta: { accion: "menu", via: "atajo", herramientas: [] }, respuesta: menu(env), adjuntos: [], estado_conversacion: { turnos: estado.turnos, pend: estado.pend } };
  }

  const inf = await obtenerInforme(env);
  const memoria = estado.turnos;
  // Lo dicho antes cuenta SOLO si el agente habia dejado una pregunta pendiente
  // ("¿a que hora?"): asi "a las 11" se une con "el lunes", pero una peticion
  // nueva no hereda el dia de otra que ya se resolvio.
  const ultimo = memoria[memoria.length - 1];
  const pendiente = ultimo && ultimo.role === "assistant" && /\?\s*$/.test(String(ultimo.content)) && !String(ultimo.content).startsWith("Hecho:");
  const anterior = pendiente ? memoria.filter((m) => m.role === "user").slice(-1).map((m) => m.content) : [];
  ctx.recientes = [...anterior, textoUsuario].join(" \n ");
  ctx.pendiente = !!pendiente;
  ctx.estado = estado;

  // La tool del PDF solo se le ofrece al modelo si pidieron el informe: con ella
  // a la mano la usaba para todo ("¿cual fue el mejor mes?" -> PDF, medido el
  // 15-oct-2026). Asi tampoco hace falta una segunda llamada para corregirlo.
  const disponibles = herramientas(env).filter((t) => t.function.name !== "enviar_informe_pdf" || pidePdf(ctx.recientes));

  const preguntar = async (historia, extra = [], tools = disponibles) => {
    const mensajes = [{ role: "system", content: systemAgente(env, inf) }, ...historia, { role: "user", content: textoUsuario }, ...extra];
    for (const modelo of MODELOS) {
      try {
        const r = await env.AI.run(modelo, { messages: mensajes, ...(tools.length ? { tools } : {}), max_tokens: 700, temperature: 0.2 });
        const p = leerLlamadas(r);
        // Solo valen las tools que se le ofrecieron en ESTA pregunta.
        p.llamadas = p.llamadas.filter((l) => tools.some((t) => t.function.name === l.nombre));
        if (p.llamadas.length || p.textoModelo) return { ...p, modelo };
      } catch (e) { /* siguiente modelo */ }
    }
    return null;
  };

  let plan = await preguntar(memoria), via = "tools";
  // EL SEGURO (nivel 2). Con historial, un modelo puede "imitar" el resultado de
  // una herramienta en vez de llamarla ("Cita agendada" sin agendar nada). Si
  // contesta algo asi sin haberla llamado, se le pregunta otra vez sin historial.
  const pareceHerramienta = (t) =>
    /^\s*(✅|📝|🗂|🗓|🗑|hecho:)/iu.test(t) || /\b(agendad|cancelad|anotad|registrad)[oa]s?\b/i.test(t);
  if (env.DB && plan && !plan.llamadas.length && pareceHerramienta(plan.textoModelo)) {
    const otra = await preguntar([]);
    if (otra && (otra.llamadas.length || !pareceHerramienta(otra.textoModelo))) { plan = otra; via = "tools (sin historial)"; }
  }
  if (!plan) {
    plan = pidePdf(textoUsuario) ? { llamadas: [{ nombre: "enviar_informe_pdf", args: {} }], textoModelo: "" }
      : { llamadas: [], textoModelo: "⚠️ El modelo de IA no respondió en este momento. Inténtelo otra vez en un minuto." };
    via = "respaldo";
  }

  const partes = [], adjuntos = [], hechos = [], ejecutadas = [];
  const ejecutar = async (llamadas) => {
    for (const ll of llamadas) {
      const firma = ll.nombre + JSON.stringify(ll.args);
      if (ejecutadas.length >= 4 || ejecutadas.some((x) => x.nombre + JSON.stringify(x.args) === firma)) continue; // nada repetido
      ejecutadas.push(ll);
      try {
        const r = await EJECUTAR[ll.nombre](env, ll.args, ctx);
        partes.push(r.texto);
        if (r.adjuntos) adjuntos.push(...r.adjuntos);
        hechos.push(r.pregunta ? "Pregunte: " + r.texto : ll.nombre + "(" + JSON.stringify(ll.args) + ")" + (r.ref ? " -> " + r.ref : ""));
      } catch (e) {
        partes.push("⚠️ No pude completar *" + ll.nombre + "*: " + String(e && e.message ? e.message : e).slice(0, 200));
        hechos.push(ll.nombre + " -> fallo");
      }
    }
  };
  // Si el mensaje pide varias cosas ("agendame ... Y anota ..."), el modelo
  // suele hacer solo la primera: se le muestra lo hecho y se le pregunta si
  // falta algo. Es el ciclo del agente, limitado a dos vueltas extra.
  const variasCosas = /\b(y|además|ademas|también|tambien)\b[\s\S]*\b(anot|apunt|agend|cancel|mand|envi|dame|muestr|regist)/i.test(textoUsuario);
  if (plan.llamadas.length) {
    if (plan.textoModelo && !pareceHerramienta(plan.textoModelo)) partes.push(plan.textoModelo);
    await ejecutar(plan.llamadas);
    for (let vuelta = 0; variasCosas && vuelta < 2 && ejecutadas.length < 4; vuelta++) {
      const mas = await preguntar(memoria, [
        { role: "assistant", content: "Hecho: " + hechos.join("; ") },
        { role: "user", content: "(Revision interna) Relee mi mensaje. Si pedi otra accion que todavia no se hizo, " +
          "llama ESA herramienta ahora. Si ya se hizo todo, responde solo: LISTO" },
      ]);
      const nuevas = ((mas && mas.llamadas) || []).filter((l) => !ejecutadas.some((x) => x.nombre === l.nombre));
      if (!nuevas.length) break;
      await ejecutar(nuevas);
      via = "tools (" + (vuelta + 2) + " vueltas)";
    }
    plan.llamadas = ejecutadas;
  } else {
    partes.push(formatoWhatsApp(plan.textoModelo));
    if (via === "tools") via = "informe";
  }
  const respuesta = partes.filter(Boolean).join("\n\n") || menu(env);

  estado.turnos = [
    ...memoria,
    { role: "user", content: textoUsuario },
    { role: "assistant", content: hechos.length ? hechos.map((h) => (h.startsWith("Pregunte: ") ? h.slice(10) : "Hecho: " + h)).join("\n") : respuesta.slice(0, 600) },
  ].slice(-8);
  await guardarConversacion(env, opciones.conversacion, estado);

  return {
    ruta: { accion: plan.llamadas.map((l) => l.nombre).join(" + ") || "responder con el informe", via, herramientas: plan.llamadas, neurons: plan.neurons, lectura: inf.via },
    respuesta,
    adjuntos,
    estado_conversacion: { turnos: estado.turnos, pend: estado.pend },
  };
}

/* ---------------------------------------------------------------------------
   BITACORA: lo ultimo que paso, para diagnosticar sin consola.
   No guarda el texto de los mensajes (gobierno de datos).
   --------------------------------------------------------------------------- */
async function anotar(env, evento) {
  try {
    const b = JSON.parse((await env.ESTADO.get("bitacora")) || "[]");
    b.unshift({ cuando: new Date().toISOString(), ...evento });
    await env.ESTADO.put("bitacora", JSON.stringify(b.slice(0, 20)));
  } catch (e) { /* no tumba nada */ }
}

const claveValida = (env, request) => !!env.CLAVE_PUENTE && request.headers.get("x-clave") === env.CLAVE_PUENTE;

// ---------------------------------------------------------------------------
// EL WORKER
// ---------------------------------------------------------------------------
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });

    // 1. Cada mensaje que manda el puente. Texto, o nota de voz en base64.
    if (url.pathname === "/api/mensaje" && request.method === "POST") {
      if (!env.CLAVE_PUENTE) return json({ ok: false, error: "Falta el secreto CLAVE_PUENTE en este Worker." }, 500);
      if (!claveValida(env, request)) return json({ ok: false, error: "Clave del puente inválida." }, 401);
      const t0 = Date.now();
      const evento = {};
      try {
        const b = await request.json();
        evento.tipo = b.audio_base64 ? "voz" : "texto";
        let textoUsuario = b.texto || "", transcripcion = null;
        if (b.audio_base64) {
          transcripcion = await transcribir(env, b.audio_base64);
          textoUsuario = transcripcion;
        }
        if (!textoUsuario.trim()) return json({ ok: false, error: "No llegó texto, o la nota de voz salió vacía." }, 400);
        const conv = /^[A-Za-z0-9_-]{6,80}$/.test(b.conversacion || "") ? b.conversacion : null;
        const r = await pensar(env, textoUsuario, { conversacion: conv, voz: !!b.audio_base64, origen: url.origin, cuerpo: b });
        Object.assign(evento, { accion: r.ruta.accion, via: r.ruta.via, resultado: "contestado" });
        return json({ ok: true, ms: Date.now() - t0, transcripcion, ...r });
      } catch (e) {
        evento.resultado = "error";
        evento.error = String(e && e.message ? e.message : e).slice(0, 300);
        return json({ ok: false, error: evento.error }, 500);
      } finally {
        evento.ms = Date.now() - t0;
        ctx.waitUntil(anotar(env, evento));
      }
    }

    // 2. El PDF del informe. ?v= es la version exacta que ya se genero.
    if (url.pathname === "/informe.pdf") {
      let pdf = null;
      const v = url.searchParams.get("v");
      if (v && /^[a-z0-9]{4,20}$/.test(v)) pdf = await env.ESTADO.get("informe:pdf:" + v, "arrayBuffer");
      if (!pdf) {
        const inf = await obtenerInforme(env, { necesitoPdf: true });
        if (inf.pdf) pdf = await env.ESTADO.get("informe:pdf:" + inf.pdf.v, "arrayBuffer");
        if (!pdf) return json({ ok: false, error: inf.errorNavegador || "No se pudo generar el PDF." }, 503);
      }
      return new Response(pdf, {
        headers: { "content-type": "application/pdf", "content-disposition": 'inline; filename="' + nombreArchivo(env) + '"', "cache-control": "no-store" },
      });
    }

    // 3. Volver a leer el informe ya (despues de publicar cambios). Con clave.
    if (url.pathname === "/api/releer") {
      if (!claveValida(env, request)) return json({ ok: false, error: "Clave del puente inválida." }, 401);
      try {
        const inf = await obtenerInforme(env, { fresco: true });
        return json({ ok: true, titulo: inf.titulo, via: inf.via, leido: inf.leido, caracteres: inf.contexto.length,
          pdf_kb: inf.pdf ? inf.pdf.kb : null, error_navegador: inf.errorNavegador || null, comienzo: inf.contexto.slice(0, 600) });
      } catch (e) {
        return json({ ok: false, error: String(e && e.message ? e.message : e) }, 500);
      }
    }

    // 4. Recordatorios para el puente (nivel 2). Con clave: marca las citas como avisadas.
    if (url.pathname === "/api/recordatorios") {
      if (!claveValida(env, request)) return json({ ok: false, error: "Clave del puente inválida." }, 401);
      if (!env.DB) return json({ ok: true, agenda: false, recordatorios: [] });
      try {
        const min = Math.min(120, Math.max(5, parseInt(url.searchParams.get("minutos"), 10) || 30));
        return json({ ok: true, agenda: true, recordatorios: await recordatoriosPendientes(env, min) });
      } catch (e) {
        return json({ ok: false, error: String(e && e.message ? e.message : e) }, 500);
      }
    }

    // 5. La agenda para pintarla en el informe (nivel 2, opcional). Es PUBLICA:
    //    si el informe es publico, cualquiera ve las citas. Ver el LEEME.
    if (url.pathname === "/api/agenda") {
      if (!env.DB) return json({ ok: false, error: "Este cerebro no tiene agenda (nivel 2 sin activar)." }, 404, CORS);
      const r = await env.DB.prepare(
        "SELECT fecha, hora, duracion_min, cliente, empresa, asunto, lugar FROM citas WHERE estado = 'programada' AND fecha BETWEEN ?1 AND ?2 ORDER BY fecha, hora"
      ).bind(ahoraCol().iso, sumarDias(ahoraCol().iso, 60)).all();
      return json({ ok: true, hoy: ahoraCol().iso, citas: r.results || [] }, 200, CORS);
    }

    // 6. Estado: que esta configurado y que paso ultimo (sin secretos ni textos).
    if (url.pathname === "/api/estado") {
      const leido = await env.ESTADO.get("informe:contexto", "json");
      return json({
        empresa: empresa(env),
        nivel: nivel(env),
        informe: env.INFORME_URL || null,
        configurado: { AI: !!env.AI, NAVEGADOR: !!env.NAVEGADOR, ESTADO: !!env.ESTADO, DB: !!env.DB, INFORME_URL: !!env.INFORME_URL, CLAVE_PUENTE: !!env.CLAVE_PUENTE },
        herramientas: herramientas(env).map((t) => t.function.name),
        ultima_lectura: leido ? { titulo: leido.titulo, via: leido.via, leido: leido.leido, caracteres: leido.contexto.length } : null,
        bitacora: JSON.parse((await env.ESTADO.get("bitacora")) || "[]"),
      });
    }

    return new Response(PAGINA.replace("__EMPRESA__", () => empresa(env).replace(/[<>&]/g, "")), { headers: { "content-type": "text/html; charset=utf-8" } });
  },
};

const PAGINA = `<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cerebro del agente de WhatsApp</title>
<style>
:root{--fondo:#F6F5F0;--tinta:#0E2036;--suave:#5b6474;--borde:#e2ded3;--verde:#29AC8A;--rojo:#D54E48}
@media (prefers-color-scheme:dark){:root{--fondo:#0E2036;--tinta:#F6F5F0;--suave:#a9b3c4;--borde:#1B3453}}
body{margin:0;background:var(--fondo);color:var(--tinta);font:15px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:28px 16px}
h1{font-weight:300;font-size:26px;margin:0 0 4px}small{color:var(--suave)}
.t{border:1px solid var(--borde);border-radius:10px;padding:14px 16px;margin:16px 0}
code{font-family:Consolas,monospace;font-size:13px}li{margin:3px 0}.ok{color:var(--verde)}.no{color:var(--rojo)}
</style></head><body><main>
<small>Diplomado en Inteligencia Artificial · UNAC · Clase 12</small>
<h1>Cerebro del agente de WhatsApp · __EMPRESA__</h1>
<p>Este Worker no se usa desde aquí: lo llama el <b>puente</b> que corre en el computador vinculado a WhatsApp.</p>
<div class="t" id="estado">Cargando…</div>
<script>
fetch("/api/estado").then(r=>r.json()).then(d=>{
 const c=d.configurado,m=k=>'<li class="'+(c[k]?"ok":"no")+'">'+(c[k]?"✔ ":"✘ ")+k+'</li>';
 document.getElementById("estado").innerHTML='<b>Nivel '+d.nivel+'</b> · informe: <a href="'+(d.informe||"#")+'">'+(d.informe||"(falta INFORME_URL)")+'</a>'+
 '<ul>'+Object.keys(c).map(m).join("")+'</ul><p>Herramientas: <code>'+d.herramientas.join(" · ")+'</code></p>'+
 (d.ultima_lectura?'<p>Última lectura del informe: '+d.ultima_lectura.leido+' ('+d.ultima_lectura.via+', '+d.ultima_lectura.caracteres+' caracteres)</p>':'<p>Todavía no ha leído el informe.</p>')+
 '<p><a href="/informe.pdf">Ver el PDF del informe</a></p>';
}).catch(()=>{document.getElementById("estado").textContent="No pude leer el estado."});
</script></main></body></html>`;
