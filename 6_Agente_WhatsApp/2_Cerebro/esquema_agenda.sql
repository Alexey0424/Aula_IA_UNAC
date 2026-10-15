-- Agenda del agente de WhatsApp (nivel 2). Base D1 de Cloudflare.
-- Se carga una sola vez:
--   npx wrangler d1 execute agenda-whatsapp --remote --file esquema_agenda.sql

CREATE TABLE IF NOT EXISTS citas (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha        TEXT NOT NULL,                 -- AAAA-MM-DD
  hora         TEXT NOT NULL,                 -- HH:MM, 24 horas, hora de Colombia
  duracion_min INTEGER NOT NULL DEFAULT 60,
  cliente      TEXT NOT NULL,
  empresa      TEXT,
  asunto       TEXT,
  lugar        TEXT,
  estado       TEXT NOT NULL DEFAULT 'programada' CHECK (estado IN ('programada', 'cancelada')),
  origen       TEXT NOT NULL DEFAULT 'whatsapp', -- whatsapp | voz
  recordada    INTEGER NOT NULL DEFAULT 0,       -- 1 = ya se mando el recordatorio
  creada       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS citas_fecha ON citas (fecha, hora);

CREATE TABLE IF NOT EXISTS notas (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente TEXT NOT NULL,
  empresa TEXT,
  nota    TEXT NOT NULL,
  origen  TEXT NOT NULL DEFAULT 'whatsapp',
  creada  TEXT NOT NULL
);
