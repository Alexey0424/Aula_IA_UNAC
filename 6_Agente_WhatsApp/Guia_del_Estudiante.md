# Agente conversacional en WhatsApp sobre el informe

**Diplomado en Inteligencia Artificial · UNAC · Clase 12 · Mg. Alexey David Velásquez Betancurt**

Su informe ya está publicado en Cloudflare (Clase 07). Con esto lo conecta a **su WhatsApp**: le
pregunta por texto o nota de voz, le contesta con lo que dice su informe y, si se lo pide, le manda
el informe en PDF. **Usted no escribe comandos:** le pega un prompt a Claude Code y él hace el resto.

---

## 1. Cómo funciona: arquitectura semihíbrida

```
su celular ──► su computador: PUENTE ──► su Cloudflare: CEREBRO ──► su INFORME publicado
 WhatsApp      entra a WhatsApp como       un Worker con IA:          lo lee y saca el PDF
               WhatsApp Web (con QR)        Whisper + LLM con tools    (el informe no se toca)
```

- **El puente** vive en su computador: entra a WhatsApp como un *dispositivo vinculado*, igual que
  WhatsApp Web. Por eso **el computador tiene que estar prendido** para que el bot conteste.
- **El cerebro** vive en su Cloudflare: lee su mensaje (si es nota de voz, primero la pasa a texto),
  lee su informe y contesta. Si usted pide el informe, usa una *tool* para mandarle el PDF.
- **El modelo escoge, el código ejecuta:** la IA decide qué hacer; el programa es el que lo hace.
- **Gratis:** todo cabe en el plan gratuito de Cloudflare. No usa la API oficial de Meta, que cobra
  cada respuesta desde el 1 de octubre de 2026.

## 2. Antes de empezar

Necesita:
- Su **informe publicado** en Cloudflare y su dirección a la mano (`https://informe-….workers.dev`).
- **Claude Code** en su computador.
- Su **celular con WhatsApp**, para escanear un QR.
- Unos **30 minutos** con internet. Lo que haga falta instalar, lo instala Claude.

> ⚠️ **El riesgo, antes que nada.** El puente es un cliente **no oficial** de WhatsApp. Usarlo va
> contra los términos de servicio de WhatsApp y puede terminar en **bloqueo del número**. Es un
> ejercicio de clase: se usa en modo **«Solo yo»**, donde el bot solo le contesta a usted en su chat
> consigo mismo. Si tiene un segundo número, mejor. Para los clientes de una empresa, la vía es la API
> oficial de Meta.

## 3. El prompt para Claude Code

Use **uno** de los dos y cambie solo la dirección de su informe.

**Opción A · si tiene el aula conectada a su Claude (Clase 04):**

```
Actualiza el aula y conecta mi informe a mi WhatsApp siguiendo la skill /agente-whatsapp
(carpeta 6_Agente_WhatsApp). Mi informe está publicado en: <la dirección de su informe>
```

**Opción B · si el docente le pasó el archivo `Instrucciones_para_Claude.md`:** abra Claude Code,
arrastre el archivo a la ventana (o escriba su ruta) y pegue:

```
Lee completo y sigue al pie de la letra el archivo Instrucciones_para_Claude.md que te adjunto.
Mi informe está publicado en: <la dirección de su informe>
```

Claude le va a preguntar cuatro cosas:
1. El nombre de su empresa como quiere verlo en WhatsApp.
2. Una o dos frases para leer bien sus números: qué es bueno y qué es malo. Si en la Clase 08 llenó
   el CAMPO 5, sirve tal cual.
3. Si quiere también la agenda (nivel 2).
4. Si quiere que el bot arranque solo al prender el computador.

Después, sin que usted haga nada:
1. Instala lo que falte y publica **el cerebro** en su Cloudflare, ajustado a su informe.
2. Le hace preguntas a su informe y le muestra qué contestó, antes de tocar WhatsApp.
3. Instala **el puente** y crea el ícono **«WhatsApp IA»** en su escritorio.
4. Abre el panel con el QR.

## 4. Lo que hace usted (solo dos cosas)

1. **Autorizar Cloudflare**, si Claude se lo pide: se abre el navegador y usted da clic en **Allow**.
2. **Escanear el QR** del panel: en el celular, WhatsApp → **⋮** o **Configuración** →
   **Dispositivos vinculados** → **Vincular un dispositivo** → apunte la cámara al QR.
   Si el QR vence, sale otro solo.

Luego abra en WhatsApp **su chat consigo mismo** («Mensaje para mí» o «Tú») y pruebe:

```
hola
¿Cómo van los indicadores?
¿Qué es lo más preocupante del informe y qué reviso primero?
Mándame el informe en PDF
🎙️ una nota de voz con cualquier pregunta
```

Las respuestas del bot llegan con 🤖 al comienzo. El PDF llega como documento.

## 5. Prender, apagar y el interruptor

**Un clic en el ícono «WhatsApp IA»** del escritorio prende el puente y abre el panel en el
navegador. Si ya estaba prendido, solo abre el panel. Si usted lo pidió, el puente **arranca solo al
prender el computador**, minimizado y en el último modo en que lo dejó.

| Modo | A quién le contesta | Desde el celular |
|---|---|---|
| 🔴 **Apagado** | A nadie. Sigue vinculado | `bot off` |
| 🟢 **Solo yo** | Solo su chat consigo mismo. **El de la clase** | `bot yo` |
| 🟠 **Abierto** | Cualquier chat individual. Se apaga solo a los 15 min | `bot abierto` |

- En el panel también está **Detener**, que cierra el programa. `bot estado` le dice en qué modo está.
- Nunca contesta grupos, estados ni canales.
- Si el computador se apaga o se suspende, el bot se calla; al volver, se reconecta solo.

## 6. Nivel 2 · la agenda (opcional)

Cuando ya funcione lo básico, si quiere, pídale a Claude:

```
Activa el nivel 2 de mi agente de WhatsApp (la agenda) siguiendo la skill /agente-whatsapp.
```

(Con la opción B: «…siguiendo el archivo Instrucciones_para_Claude.md».)

Después le puede decir, escrito o por voz:
- «Agéndame una cita mañana a las 3 con Julián de Argos»
- «¿Qué tengo esta semana?» · «Cancela la de Argos»
- «Anota que Julián pidió 5 % de descuento» · «¿Qué hemos hablado con Julián?»

Treinta minutos antes de cada cita le llega un ⏰. Si le falta el día o la hora, el agente pregunta:
no se los inventa.

> Si pide que la agenda también se vea en su informe: **si el informe es público, la agenda también
> lo es.** Con clientes reales, mejor consultarla solo por WhatsApp.

## 7. Límites y cuidados

| Límite | Qué significa |
|---|---|
| **10.000 neurons al día** (la IA gratis de Cloudflare) | En cada pregunta el modelo lee su informe completo: alcanza para unas decenas de mensajes al día. Se recargan a las **7:00 p. m.** hora de Colombia. No haga pruebas largas el día en que lo va a mostrar |
| **Navegador de Cloudflare gratis** | 10 minutos al día. Por eso el informe se relee cada 15 minutos y el PDF se rehace cada hora. Si cambia su informe, el agente lo ve a los 15 minutos |
| **Gráficas sin números** | Lo que una gráfica pinta sin el número escrito, el agente no lo lee. Sí lee tarjetas, tablas y los datos que trae la página |

> 🔑 **La carpeta `sesion_whatsapp` es la llave de su WhatsApp.** Quien la copie, entra. No se
> comparte ni se sube a ningún lado. Claude la deja en su computador, en una carpeta que no se sube.

**A un agente no se le cree: se le prueba.** Pregúntele cosas cuya respuesta usted ya sabe y compare
con su informe antes de mostrárselo a alguien. Para la sustentación sirve contar qué falló y cómo se
corrigió.

## 8. Si algo falla

Dígale a su Claude, con sus palabras, qué pasó («el bot no contesta», «no me llega el PDF», «el QR
no aparece»). Las `Instrucciones_para_Claude.md` traen la tabla de problemas y cómo se arregla cada uno.
