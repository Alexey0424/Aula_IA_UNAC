# Aula IA UNAC

Materiales del **II Diplomado en Inteligencia Artificial** — Especialización en Alta Gerencia,
Corporación Universitaria Adventista (UNAC), Medellín, Colombia.

Docente y asesor temático: **Mg. Alexey David Velásquez Betancurt** — MSc. Ingeniería de
Inteligencia Artificial.

## Qué es esto

Esta carpeta es **el aula conectada**: al abrirla con Claude (Claude Code o la app de
escritorio, pestaña Code), su Claude lee automáticamente las instrucciones del curso y se
convierte en su **asesor del proyecto de grado**: conoce los criterios de las 4 entregas,
las guías de clase, los notebooks de laboratorio y las referencias verificadas.

## Cómo conectarse (una sola vez, ~5 minutos)

1. Abra Claude (app de escritorio → pestaña **Code**, o `claude` en la terminal) en la carpeta
   `C:\Curso_IA_UNAC` (créela; sin acentos, sin espacios, fuera de OneDrive).
2. Escríbale, tal cual:
   > Clona el repositorio https://github.com/Alexey0424/Aula_IA_UNAC dentro de esta
   > carpeta y muéstrame qué archivos quedaron.
3. Cierre esa sesión y abra una nueva **dentro** de la carpeta `Aula_IA_UNAC` que quedó creada.
4. Cuando pregunte si confía en la carpeta, diga que sí (una única vez).
5. Compruebe: escriba `/context` — debe aparecer el `CLAUDE.md` del curso en *Memory files*.
6. Pruebe: escriba `/entrega-1` y luego *"evalúa mi idea de proyecto contra estos criterios"*.

Para traer las novedades cada semana: escriba `/actualizar-curso`.

## Estructura

| Carpeta | Contenido |
|---|---|
| `1_Guias_de_Clase/` | Guías y diapositivas de cada clase (incluidas las rayadas en vivo) |
| `2_Criterios_Proyecto_de_Grado/` | Criterios oficiales y rúbricas de las 4 entregas |
| `3_Referencias/` | Referencias verificadas, con fuente y licencia |
| `4_Notebooks_Colab/` | Plantillas de laboratorio para Google Colab |
| `mis_entregas/` | **Su carpeta.** Todo su trabajo va aquí (no se sube a este repositorio) |

## Las dos reglas

1. **Su trabajo va en `mis_entregas/`.** No edite el resto del material: lo actualiza el docente.
2. Este repositorio es **público**: no guarde aquí datos de su empresa ni información personal.

## Plan B — sin clonar (claude.ai o emergencias)

Agregue el conector **GitMCP** en claude.ai (Configuración → Connectors → *Add custom
connector*) con la URL: `https://gitmcp.io/Alexey0424/Aula_IA_UNAC` — su Claude podrá
consultar el material sin tener los archivos en su computador.
