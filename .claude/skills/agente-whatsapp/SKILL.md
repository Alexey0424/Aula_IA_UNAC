---
name: agente-whatsapp
description: Conectar el informe publicado del estudiante a su WhatsApp con el kit 6_Agente_WhatsApp (puente semihibrido en su computador + cerebro en su Cloudflare), paso a paso y sin que el estudiante escriba comandos. Usar cuando el estudiante pida conectar su informe o tablero a WhatsApp, montar el agente de WhatsApp, activar la agenda (nivel 2), o prender, apagar, desmontar o arreglar el puente.
---

# Agente de WhatsApp sobre el informe · Clase 12

**Lea completo y siga al pie de la letra `6_Agente_WhatsApp/Instrucciones_para_Claude.md`.**
Ahí está todo: qué se construye, las reglas, de dónde sale el kit, el cerebro en Cloudflare, el
puente en el computador, el ícono «WhatsApp IA», la prueba con el estudiante, el nivel 2 (agenda),
el script de prueba, los límites, la tabla de problemas y cómo desmontarlo.

Antes de abrirlo, `git pull --ff-only` en el aula (skill `/actualizar-curso`), para tener la última
versión del kit.

Lo esencial, por si acaso:

1. El estudiante **no escribe comandos**: solo autoriza Cloudflare (si hace falta) y escanea el QR.
2. Su copia de trabajo va en **`mis_entregas/agente_whatsapp/`**; nada suyo dentro de `6_Agente_WhatsApp/`.
3. **`sesion_whatsapp/` y `config.json` son llaves**: nunca se muestran ni se suben. La clave no se imprime.
4. Modo de clase **«Solo yo»**, y antes de empezar se le dice el riesgo: es un cliente no oficial de
   WhatsApp (va contra sus términos; puede terminar en bloqueo del número).
5. **No se modifican `worker.js` ni `puente.mjs`**: solo `wrangler.toml` y `config.json`.
