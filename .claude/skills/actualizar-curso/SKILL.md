---
name: actualizar-curso
description: Traer las novedades del aula (git pull) - nuevas guias, diapositivas rayadas, notebooks y criterios publicados por el docente. Usar cuando el estudiante pida actualizar el curso o los materiales.
---

# Actualizar el material del curso

## Procedimiento

1. Verifique que está dentro de la carpeta del aula (existe `CLAUDE.md` y la carpeta
   `1_Guias_de_Clase/` en la raíz).
2. Ejecute:
   ```
   git pull --ff-only
   ```
3. **Si funciona:** dígale al estudiante, en una lista corta y en español, qué archivos nuevos
   o actualizados llegaron (`git log --oneline -5` y los nombres de archivos cambiados) —
   por ejemplo: "llegaron las diapositivas rayadas de la Clase 04 y un notebook nuevo".
4. **Si falla con "divergent branches" o conflicto:** casi seguro el estudiante editó un
   archivo del curso por accidente. Explíquelo sin regaño: "usted cambió un archivo del
   material del curso; su trabajo debe ir en `mis_entregas/`". Luego ofrezca la reparación:
   - Mueva cualquier archivo propio que esté por fuera de `mis_entregas/` hacia `mis_entregas/`.
   - Descarte los cambios sobre el material del curso con `git checkout -- <archivo>` 
     (confirmando antes con el estudiante qué se va a descartar).
   - Vuelva a correr `git pull --ff-only`.
5. **Nunca** haga `git push` desde el aula: el aula es de solo lectura para el estudiante.
