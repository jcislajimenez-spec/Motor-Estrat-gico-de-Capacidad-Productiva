PLAN DE IMPLEMENTACIÓN
Motor Estratégico · Programación real
2026-06-22 · V06 CIERRE
Idea central: este plan recoge el estado real del módulo tras completar la corrección de la regresión del modo secuencial y las aclaraciones de UI (junio 2026). Actualiza el V05 CIERRE con las fases adicionales ejecutadas y deja claro qué falta para que Programación real sea operativa.
Fecha: 2026-06-22
Versión: V06 CIERRE (versión vigente)
Sustituye y corrige: Plan V05 CIERRE (2026-06-21). Incorpora corrección de regresión secuencial (commit 0e1db08f) y aclaraciones de textos de UI (commit 4372f181).
Documento base: Plan V05 CIERRE + Reglas operativas de simulación v0.5.
Regla de control: Este documento no autoriza cambios de código. Cada fase necesita aprobación expresa, ejecución controlada y validación.
Conclusión ejecutiva: la base funcional está madura y el modo secuencial ya funciona correctamente para todos los tipos de proyecto. Los textos de UI ya describen con precisión el comportamiento de cada modo. Quedan pendientes: exportación a Excel de la simulación activa, auditoría de casuísticas y limpieza visual.

# 0. Historial de revisiones

## 0.1. Evolución de versiones
2026-05-25 · V01: Plan inicial para arrancar Programación real.
2026-05-28 · V02: Plan vivo con fases técnicas y funcionales.
2026-05-29 · V03: Reescritura en lenguaje funcional.
2026-05-29 · V04: Versión corregida. Recupera los pendientes reales.
2026-06-20 · V04.1 (Anexo): Ajustes Codex primera ronda incorporados.
2026-06-21 · V05 CIERRE: Incorpora regla de exclusividad de línea, distinción de carga y semana de transición con confirmación.
2026-06-22 · V06 CIERRE (versión vigente): Incorpora corrección de regresión del modo secuencial (bug: lote_divisible/fase_transferible/desconocido en modo secuencial se comportaban como paralelo). Incorpora aclaraciones de textos de UI. Actualiza estado de fases ejecutadas.

## 0.2. Cambios exactos de V06 respecto a V05

- **Fase Hotfix A — Corrección regresión secuencial:** marcada como ejecutada y validada (commit `0e1db08f`).
- **Fase 5A — Aclaraciones de UI:** marcada como ejecutada y validada (commit `4372f181`).
- **Reglas operativas:** actualizadas a v0.5.
- **Estado del módulo (sección 2):** actualizado para reflejar que el modo secuencial ya funciona correctamente para todos los tipos.

# 1. Objetivo del documento

- Guiar la implementación pendiente de Programación real sin perder lo que ya funciona.
- Explicar las fases en lenguaje de usuario: qué se ve, qué se decide y cómo se valida.
- Definir qué falta para que el módulo deje de ser una prueba funcional y se convierta en una herramienta operativa útil.
Regla principal: si el usuario funcional no entiende una fase, esa fase no entra en el plan principal.

# 2. Estado real actual del módulo

## 2.1. Lo que ya funciona (v0.5)

- Cargar Excel de Programación real.
- Calcular carga por proyecto, semana y línea.
- Detectar conflictos de capacidad.
- Mostrar Gantt de Plan real y Simulación.
- Primera ronda: mover proyecto completo a otra línea.
- Primera ronda: ampliar semanas.
- Simulación activa acumulada sin tocar el Plan real.
- Segunda ronda: detectar pendientes vivos tras la primera acción.
- Segunda ronda: ampliar semanas en destino.
- Segunda ronda: mover/reprogramar exceso.
- **Modo Paralelo:** reparto proporcional en las mismas semanas del conflicto.
- **Modo Secuencial:** reparto proporcional igual que Paralelo, pero en cascada temporal después del tramo principal. Funciona correctamente para todos los tipos de proyecto (equipo único, lote divisible, fase transferible, desconocido).
- Leer Tipo de proyecto y Nº unidades desde Excel.
- Mostrar aviso visual según tipo de proyecto al elegir Reprogramar residual.
- Textos de UI que describen correctamente el comportamiento de cada modo.
- Banner de simulación activa con referencia al botón "Reiniciar simulación".

## 2.2. Lo que NO está cerrado todavía

- No está cerrado el Excel final de salida de la simulación activa (Exportación).
- No está demostrado en un documento de validación que todas las casuísticas de las reglas operativas v0.5 estén cubiertas con casos reales.
- No está completamente cerrada la lógica de exceso para todos los subtipos: la auditoría de casuísticas (Fase 8) está pendiente.
- No está limpia la lectura visual de la pantalla: hay bloques y tablas que pueden confundir al usuario.
- No está cerrado un manual de usuario final.
- La exportación a Excel de la simulación activa no está implementada.

# 3. Flujo funcional que debe respetarse

## 3.1. Plan real
Es el Excel original cargado por el usuario. No se modifica nunca. Es la foto base contra la que se compara todo.

## 3.2. Simulación activa
Es la foto de trabajo acumulativa. Cuando el usuario aplica una acción, la app no cambia el Plan real: crea o actualiza una simulación. El usuario puede volver atrás descartando la simulación con el botón "Reiniciar simulación".

## 3.3. Primera ronda
Sirve para tomar la primera decisión importante sobre un proyecto que no cabe bien.
- Mover proyecto completo: preferible si otra línea compatible encaja mejor.
- Ampliar semanas: alternativa fuerte si no hay línea mejor o si se acepta alargar duración.
- Mover exceso no es opción normal de primera ronda en esta versión.

## 3.4. Segunda ronda / ajustar pendientes
Sirve para actuar sobre lo que sigue vivo después de la primera acción.
- Ampliar semanas en destino: mantener el proyecto y repartir la carga en más semanas.
- Mover/reprogramar exceso: actuar solo sobre la parte sobrante, no sobre todo el proyecto.
- No actuar: aceptar que ese conflicto queda vivo por ahora.
- Se puede combinar acciones sobre proyectos distintos en la misma segunda ronda.

## 3.5. Regla de modos: Paralelo vs. Secuencial
El exceso se reparte con fracciones iguales entre destinos en ambos modos (50/50, 33/33, 25/25, etc.).
- Paralelo: las fracciones se colocan en las mismas semanas donde aparece el exceso.
- Secuencial: las fracciones se colocan en cascada temporal después del tramo principal del proyecto.
- La diferencia es temporal, no de porcentaje.

# 4. Fases ejecutadas y validadas

## Fase 1 — Nombre visible de la acción
Estado: **EJECUTADA Y VALIDADA**
Qué se hizo: Cambiar el lenguaje de la acción para que el usuario entienda que no se mueve todo el proyecto, sino la parte sobrante. Aparece como "Reprogramar residual".

## Fase 2 — Leer Tipo de proyecto y Nº unidades
Estado: **EJECUTADA Y VALIDADA**
Qué se hizo: El Excel admite los campos de tipo de proyecto. Los Excel antiguos siguen cargando.

## Fase 3 — Guardar esos datos en la simulación
Estado: **EJECUTADA Y VALIDADA**
Qué se hizo: El tipo de proyecto y número de unidades quedan guardados cuando se aplica una acción.

## Fase 4 — Aviso visual por tipo de proyecto
Estado: **EJECUTADA Y VALIDADA**
Qué se hizo: Se muestra aviso al elegir mover/reprogramar exceso según el tipo de proyecto. Equipo único muestra aviso fuerte; lote divisible y fase transferible muestran orientación; desconocido avisa.

## Fase Hotfix A — Corrección de regresión del modo secuencial
Estado: **EJECUTADA Y VALIDADA** (fuera del plan original)
Commit: `0e1db08f` — Fix sequential residual start for all project types
Qué se hizo: Se corrigió la regresión introducida en commit `95de844f` que hacía que los tipos lote_divisible, fase_transferible y desconocido en modo Secuencial se comportaran como Paralelo (usaban `min(_semanas_afectadas)` en lugar de `max(_semanas) + 1`). La corrección aplica `max(_semanas) + 1` a todos los tipos de proyecto en modo secuencial.
Validación: modo secuencial y paralelo ahora producen resultados distintos para todos los tipos de proyecto.

## Fase 5A — Aclaraciones de textos de UI
Estado: **EJECUTADA Y VALIDADA** (fuera del plan original)
Commit: `4372f181` — Clarify programming real simulation texts
Qué se hizo: Se actualizaron tres textos de interfaz:
1. Radio Paralelo/Secuencial: describe que la diferencia es temporal, no de porcentaje.
2. Orientación para lote divisible: alineada con la regla vigente.
3. Banner de simulación activa: añade referencia al botón "Reiniciar simulación".
Validación: los textos de UI describen correctamente el comportamiento tras el hotfix.

# 5. Hoja de ruta pendiente

## Fase 6 — Textos de orientación en primera ronda
Qué vamos a hacer: Añadir una ayuda breve que explique cuándo conviene mover el proyecto completo y cuándo conviene ampliar semanas.
Por qué aporta valor: Evita que el usuario elija sin criterio entre dos alternativas válidas.
Qué debe ver el usuario: Una frase clara junto a las alternativas de primera ronda.
Qué no se toca: No se toca cálculo, Gantt, Plan real ni segunda ronda.
Riesgo: Muy bajo

## Fase 7 — Exportar simulación activa a Excel
Qué vamos a hacer: Crear un Excel descargable con el resultado de la simulación activa.
Por qué aporta valor: Cierra el ciclo: el planificador debe poder compartir la simulación sin depender de capturas de pantalla.
Qué debe ver el usuario: Un botón de descarga. El Excel debe mostrar Plan real vs Simulación, acciones aplicadas, déficit inicial, déficit final y mejora conseguida.
Qué no se toca: No se toca el cálculo. La exportación copia lo que la app ya muestra.
Riesgo: Medio

## Fase 8 — Auditoría funcional de casuísticas v0.5 contra la app real
Qué vamos a hacer: Revisar caso por caso si las reglas operativas v0.5 están cubiertas por la app actual.
Por qué aporta valor: Antes de programar más, hay que saber exactamente qué falta y qué ya está resuelto.
Qué debe ver el usuario: No hay cambio visible; es una revisión con lista de casos.
Qué no se toca: No se toca código.
Riesgo: Bajo si es solo análisis

## Fase 9 — Cerrar comportamiento de mover/reprogramar exceso según tipo de proyecto
Qué vamos a hacer: Implementar, si se aprueba tras la Fase 8, la lógica diferenciada para todos los subtipos.
Qué no se toca: No se toca nada sin la auditoría de Fase 8 y aprobación expresa.
Riesgo: Alto — requiere división en subfases.

## Fase 10 — Diagnóstico claro para "No actuar"
Qué vamos a hacer: Cuando el usuario elige No actuar, la app debe dejar claro qué conflicto queda vivo.
Qué debe ver el usuario: Un texto sencillo: "queda X h de déficit en línea Y semana Z".
Riesgo: Bajo

## Fase 11 — Limpieza visual de Programación real
Qué vamos a hacer: Ordenar la pantalla para reducir ruido y mejorar la jerarquía visual.
Qué no se toca: No se crean tablas nuevas sin aprobación. No se toca cálculo.
Riesgo: Medio

## Fase 12 — Decidir si hace falta tercera iteración
Solo si el uso real demuestra que tras segunda ronda quedan conflictos frecuentes.
Riesgo: Pendiente futuro

## Fase 13 — Manual de usuario final
Qué vamos a hacer: Crear una guía de uso de Programación real de principio a fin.
Por qué aporta valor: Permite que otra persona use el módulo sin depender de explicaciones externas.
Riesgo: Bajo

# 6. Qué significa "módulo acabado"

No se considerará acabado solo porque la app no dé error. Se considerará acabado cuando permita decidir, demostrar y exportar una simulación útil.

1. Cargar una programación real desde Excel.
2. Detectar conflictos de capacidad de forma clara.
3. Aplicar una primera ronda razonable.
4. Aplicar una segunda ronda sobre pendientes vivos.
5. Distinguir correctamente equipo único, lote divisible, fase transferible y desconocido, al menos para no proponer acciones engañosas.
6. Mostrar déficit inicial, déficit final y mejora conseguida.
7. Exportar a Excel una simulación activa entendible.
8. Tener una pantalla que ayude a decidir y no obligue a interpretar veinte tablas.
9. Tener un manual de uso que una persona pueda seguir sin conocer el código.

# 7. Límites y cosas que no se tocan sin aprobación

- No se toca el Plan real: siempre queda intacto.
- No se toca engine.py salvo error demostrado y aprobado.
- No se toca Gantt si no hay bug visible.
- No se crean nuevas tablas o paneles sin aprobación expresa.
- No se cambia la lógica de mover/reprogramar exceso sin la auditoría de Fase 8.
- No se abre reparto paralelo avanzado sin caso real y validación específica.

# 8. Próximo paso operativo recomendado

Siguiente paso: Fase 7 (exportar simulación activa a Excel) o Fase 8 (auditoría de casuísticas). Se recomienda hacer primero la Fase 8 porque sin ella no se puede confirmar que la Fase 7 exporta los datos correctos.

Paso inmediato 1: Aprobar este plan V06 como referencia actualizada.
Paso inmediato 2: Decidir si la siguiente prioridad es Fase 7 (exportación) o Fase 8 (auditoría).
Paso inmediato 3: No abrir Fase 9 sin completar la Fase 8.

# 9. Nota técnica fuera del plan funcional

- Las protecciones internas no deben aparecer en el plan funcional salvo que correspondan a algo visible y validable en pantalla.
- Si aparece un fallo técnico reproducible, se abrirá una fase de depuración separada con pasos exactos.
- No se acepta tocar código por hipótesis abstractas sin caso real.

---

# 10. Trazabilidad de commits de referencia

Los siguientes commits son la base de implementación del módulo Programación real hasta la versión V06. Cualquier análisis de comportamiento o auditoría debe partir de estos commits.

| Commit | Descripción | Impacto principal |
|---|---|---|
| `78b9280a` | Prevent multiple first-round alternatives per project | Bloquea que un proyecto tenga más de una alternativa de primera ronda aplicada simultáneamente. Estabiliza la lógica de exclusividad de acciones por proyecto. |
| `036cb323` | Accumulate first-round alternatives on active simulation | La simulación activa acumula correctamente las alternativas de primera ronda. Cada acción aplicada se suma a la foto de trabajo sin resetear las anteriores. |
| `0d286768` | Allow mixed second-round actions with visible warnings | Permite combinar acciones distintas (ampliar + mover exceso) sobre proyectos distintos en la misma segunda ronda. Muestra advertencias visibles cuando se mezclan acciones. |
| `0e1db08f` | Fix sequential residual start for all project types | Corrige la regresión de `95de844f`. El cursor secuencial (`_sem_cursor`) se inicializa en `max(_semanas) + 1` para todos los tipos de proyecto, no solo para equipo_unico. |
| `4372f181` | Clarify programming real simulation texts | Actualiza tres textos de UI: radio Paralelo/Secuencial, orientación para lote divisible y banner de simulación activa. Todos describen correctamente la diferencia temporal (no de porcentaje) entre modos. |

**Commits de contexto histórico (no de referencia primaria para V06):**

| Commit | Descripción |
|---|---|
| `ba7867f0` | Implement sequential excess move exclusivity — regla de exclusividad de línea |
| `95de844f` | Fix sequential residual start for single equipment — commit que introdujo la regresión corregida en `0e1db08f` |
| `fcd86588` | Fix blocked-week partial residual placement — regla C3: usa capacidad libre de la semana bloqueada antes de detener |
| `951e95d1` | Add full project move recalculation — recálculo completo al mover proyecto |

---

*Fin del plan V06 CIERRE — Programación real*
