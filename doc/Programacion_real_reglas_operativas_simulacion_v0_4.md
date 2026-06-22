# PROGRAMACIÓN REAL
## Reglas operativas de simulación
### v0.4 — Fuente de verdad funcional antes de tocar código

---

**Estado:** v0.4 vigente  
**Fecha:** 2026-06-22  
**Sustituye en los puntos indicados:** v0.3 (2026-06-21)  
**Documento base:** v0.3 + Auditoría funcional 2026-06-22 + decisión Opción A vs B

> **Qué es este documento:** Evolución ordenada de v0.3. No elimina las reglas anteriores: las confirma, amplía o matiza. Lo que no aparece como cambiado se mantiene igual que en v0.3.
>
> **Qué no es:** No es una especificación de código ni una autorización para modificar app.py o engine.py.
>
> **Relación con v0.3:** El documento v0.3 permanece intacto como referencia histórica. v0.4 prevalece en los puntos que especifica. Lo no mencionado en v0.4 se rige por v0.3.

---

## 1. Qué cambia respecto a v0.3

| ID | Área | Naturaleza del cambio |
|---|---|---|
| D1 | Mover proyecto completo | Nueva regla cerrada: Opción A, déficit vivo en destino semana a semana |
| D2 | M3 (eliminación de origen) | Siempre incondicional; sin rama de "movimiento parcial" |
| D3 | Checkbox de transición | Texto corregido; solo confirma solapamiento; no autoriza parcial |
| D4 | Horizonte del movimiento | Definido: tramo original del proyecto (semana_inicio a semana_fin_actual) |
| D5 | F7 matizado por tipo de acción | F7 aplica con matiz en mover completo: puede recalcular duración solo para acortar dentro del tramo original; plenamente en reprogramar residual |
| D6 | Combinación mover + ampliar | Bloqueada explícitamente en primera ronda |
| D7 | Acortamiento de semanas | Permitido si destino tiene más capacidad; solo dentro del tramo original |

Ninguno de estos cambios contradice el espíritu de v0.3. Varios cierran pendientes que v0.3 dejaba explícitamente abiertos (especialmente P6).

> **Relación con el commit revertido 951e95d1:** La función `_simulate_prog_move_full` de ese commit implementaba una rama M3 de "movimiento parcial" que dejaba horas residuales en origen cuando el destino no absorbía todo. Eso viola la regla base de "mover completo". v0.4 cierra esa regla antes de volver al código.

---

## 2. Objetivo y alcance

### 2.1. Objetivo operativo

- Cerrar el pendiente P6 de v0.3: "Mover proyecto completo con regla de exclusividad."
- Definir exactamente qué ocurre cuando se aplica "Mover proyecto completo" en primera ronda.
- Separar sin ambigüedad las acciones de primera ronda de las de segunda ronda.
- Eliminar la posibilidad de que la app deje carga residual en origen tras una acción de mover completo.
- Definir el comportamiento del déficit vivo en destino.
- Cerrar la regla del checkbox de transición.

### 2.2. Lo que v0.4 NO cambia

- Taxonomía de proyecto (Sección 3 de v0.3): equipo único, lote divisible, fase transferible, desconocido.
- Reglas físicas F1–F9 (v0.3): se mantienen íntegras.
- Reprogramar residual (Sección 7 de v0.3): se mantiene íntegra.
- No buscar huecos discontinuos, C2, C3 (Sección 8 de v0.3): se mantiene para reprogramar residual.
- Saturación vs. déficit (Sección 10 de v0.3): se mantiene.
- Plan real vs. Simulación activa (Sección 13 de v0.3): se mantiene.
- Reglas bloqueantes B1–B8 (Sección 11.1 de v0.3): se mantienen, más las nuevas de v0.4.

---

## 3. "Mover proyecto completo" — Primera ronda

### 3.1. Definición

"Mover proyecto completo" en primera ronda significa trasladar la totalidad de la carga del proyecto de la línea origen a una línea destino compatible. Esta acción tiene una única semántica posible: después de aplicarla, el proyecto no tiene ninguna hora en la línea origen.

### 3.2. Reglas cerradas (D1–D7)

| ID | Regla | Descripción |
|---|---|---|
| MV-01 | Origen siempre vacío | Tras aplicar "mover completo", la línea origen queda sin ninguna hora del proyecto. Sin excepción. |
| MV-02 | Eliminación incondicional de origen | M3 elimina TODAS las filas del proyecto en la línea origen, independientemente de si el destino absorbe todo o no. No existe rama de "movimiento parcial". |
| MV-03 | Déficit vivo en destino | Si el destino no absorbe toda la carga dentro del tramo original del proyecto, las horas no absorbidas quedan como déficit vivo en destino, semana a semana. Nunca regresan a origen. |
| MV-04 | Horizonte máximo = tramo original | El movimiento opera dentro del mismo rango temporal que ocupaba el proyecto en origen: de semana_inicio a semana_fin_actual. No se crean semanas nuevas automáticamente. |
| MV-05 | Sin ampliación automática | La acción "mover completo" no puede generar una duración mayor que semana_fin_actual − semana_inicio. Si el destino no absorbe todo en ese tramo, el sobrante es déficit vivo en destino. |
| MV-06 | Acortamiento permitido | Si el destino tiene más capacidad disponible real (capacidad nominal de destino menos carga ya existente en destino por semana) y el proyecto completo cabe en menos semanas dentro del tramo original usando esa capacidad disponible real, el movimiento puede acortar la duración. El acortamiento se muestra en vista previa antes de confirmar; si el usuario pulsa Aplicar, el resultado incluye ese acortamiento. No se amplían semanas. Si la capacidad disponible real no basta (por carga preexistente), no se fuerza el acortamiento y el déficit queda vivo en destino semana a semana. No se usa la capacidad nominal para decidir el acortamiento ignorando la carga preexistente. |
| MV-07 | Sin mezcla mover + ampliar | La UI no permite seleccionar simultáneamente "Mover línea" y "Ampliar semanas" para el mismo proyecto en el mismo paso de primera ronda. Si se seleccionan ambas, aparece un error bloqueante. |
| MV-08 | Checkbox de transición corregido | Ver Sección 4 de este documento. |
| MV-09 | Conflicto visible en destino | Si el movimiento genera semanas con carga > capacidad en destino, la app muestra el conflicto como déficit vivo. No lo oculta, no lo suaviza, no lo resuelve automáticamente. |
| MV-10 | F7 matizado en mover completo | En Mover proyecto completo, F7 queda matizado así: puede recalcular duración solo para acortar dentro del tramo original cuando el destino tiene más capacidad y el proyecto completo cabe sin ampliar semanas. F7 no autoriza alargar automáticamente. Si no cabe en menos semanas, el déficit queda vivo en destino semana a semana (Opción A). |
| MV-11 | Conservación de horas | Suma de horas del proyecto en destino tras el movimiento = suma de horas del proyecto en origen antes del movimiento. La regla B3 de v0.3 debe cumplirse exactamente. |
| MV-12 | Segunda ronda decide el déficit | El déficit vivo generado por "mover completo" no se resuelve automáticamente. La segunda ronda decide entre ampliar semanas, reprogramar residual o no actuar. |

### 3.3. Opción A — Déficit vivo semana a semana (decisión adoptada)

v0.4 adopta Opción A como regla para representar el déficit **cuando el destino no absorbe toda la carga** dentro del tramo original.

> **Distinción importante:** Opción A y el acortamiento no son contradictorios; regulan casos distintos.
> - **Caso de acortamiento:** el destino tiene más capacidad y el proyecto cabe en menos semanas. El movimiento produce un resultado con menos semanas. No hay déficit. Opción A no aplica aquí.
> - **Caso de déficit (Opción A):** el destino no absorbe todo dentro del tramo original. Las horas del proyecto pasan a destino con el mismo patrón semanal; las semanas donde la carga supera la capacidad muestran déficit vivo. Se descarta Opción B (pico acumulado al final).

**Opción A (caso de déficit):** Las filas del proyecto se mueven a la línea destino manteniendo el mismo patrón semanal (mismas semanas, mismas horas por semana que tenía en origen). Si en alguna semana la carga del proyecto en destino, sumada a la carga preexistente en esa línea, supera la capacidad nominal, esa semana muestra déficit vivo. El déficit es orgánico: emerge del cálculo de capacidad existente en la app, no de una representación especial.

**Opción B descartada para v0.4:** Acumular artificialmente el déficit en la última semana del tramo. Descartada porque:
- Distorsiona la presión semanal real del proyecto.
- El pico artificial no representa cómo trabaja una línea de producción.
- Dificulta la toma de decisiones en segunda ronda (el planner no ve qué semanas individuales tienen problema).
- Requiere una representación especial en el DataFrame que añade complejidad sin beneficio operativo.

### 3.4. Casuísticas de "Mover proyecto completo"

| Escenario en destino | Comportamiento correcto v0.4 | Lo que no debe ocurrir |
|---|---|---|
| Destino con más capacidad disponible real que origen | Vista previa muestra el acortamiento posible; si el usuario aplica, el proyecto queda en destino en menos semanas dentro del tramo original; origen = 0 h | Acortamiento sin aviso previo; ampliación automática de semanas |
| Destino con más capacidad nominal pero carga preexistente en algunas semanas | El acortamiento solo se calcula con la capacidad disponible real (nominal − carga preexistente por semana). Si el proyecto cabe en menos semanas con esa capacidad real, se muestra el acortamiento. Si no cabe, se muestra déficit vivo en destino semana a semana. Origen = 0 h en todos los casos. | Forzar acortamiento usando solo capacidad nominal ignorando carga preexistente; ocultar conflicto con carga existente |
| Destino con igual capacidad que origen | Proyecto va con mismo patrón; sin diferencia de semanas; origen a 0 h | Ninguno aplica |
| Destino con menos capacidad que origen | Proyecto va con mismo patrón; semanas donde carga > capacidad muestran déficit; origen a 0 h | Ampliar semanas automáticamente; dejar horas en origen |
| Primera semana del destino con carga de otro proyecto | Aviso de transición + checkbox; tras confirmación, proyecto se mueve completo | Parar el movimiento sin mover nada; ocultar el solapamiento |
| Semanas posteriores del destino con carga de otro proyecto | Proyecto se mueve completo; semanas compartidas muestran conflicto o déficit si suma > capacidad | Dejar horas en origen de esas semanas |
| Ningún destino compatible | No actuar con diagnóstico: "no existe destino compatible" | Proponer mover a incompatible |

---

## 4. Checkbox de transición

### 4.1. Cuándo aparece

El checkbox de transición aparece cuando la primera semana que el proyecto ocuparía en la línea destino ya tiene carga de otro proyecto/modelo.

### 4.2. Qué confirma

El usuario acepta el solapamiento con otro proyecto/modelo en la primera semana del destino y entiende que habrá conflicto visible en esa semana.

### 4.3. Texto correcto

```
"Confirmo que hay carga de otro proyecto en S[X] de [DEST] y aplico el movimiento completo."
```

### 4.4. Texto prohibido

El texto del checkbox **no puede contener** ninguna de las siguientes expresiones:
- "movimiento parcial"
- "acepto el parcial"
- "movimiento incompleto"

### 4.5. Qué autoriza y qué no autoriza

| El checkbox SÍ autoriza | El checkbox NO autoriza |
|---|---|
| Aplicar el movimiento completo a pesar del solapamiento | Ampliar semanas |
| Aceptar que habrá conflicto visible en la primera semana | Dejar carga en origen |
| Continuar el movimiento a las semanas siguientes | Movimiento parcial |
| — | Resolver automáticamente el solapamiento |

### 4.6. Comportamiento si no se confirma

Si el checkbox es requerido y no está marcado, el botón Aplicar muestra un error bloqueante:
```
"Hay una semana de transición en S[X]. Confirma el checkbox antes de aplicar."
```

### 4.7. Comportamiento tras confirmación

El movimiento se aplica íntegro. MV-01 y MV-02 se cumplen. El origen queda vacío. El solapamiento queda como conflicto visible en destino.

---

## 5. Primera ronda vs segunda ronda

### 5.1. Pregunta de primera ronda

El proyecto, tal como está en el plan real, no cabe o está mal ubicado. ¿Existe una línea compatible donde el proyecto completo encaje mejor?

| Situación | Recomendada | Permitida | No recomendada | Bloqueada |
|---|---|---|---|---|
| Hay línea compatible y encaja mejor | Mover completo | — | Residual en 1ª ronda | Mover + ampliar simultáneo |
| No hay destino compatible | Ampliar semanas | No actuar | Mover a incompatible | — |
| Destino compatible con conflicto | Mover completo con advertencia | — | Ocultar conflicto | Mover + ampliar simultáneo |
| Equipo único | Mover completo o ampliar | — | Residual paralelo | — |
| Lote divisible | Mover completo | Ampliar | — | Paralelo sin control |
| Tipo desconocido | Mover completo o ampliar | Residual avanzado con advertencia | — | Residual automático |

### 5.2. Pregunta de segunda ronda

Ya se aplicó una primera acción. Si sigue habiendo conflicto (déficit vivo en destino o en origen), ¿qué ajuste tiene sentido?

| Situación | Recomendada | Permitida | No recomendada | Bloqueada |
|---|---|---|---|---|
| Déficit vivo en destino tras mover completo | Ampliar semanas | Reprogramar residual | No actuar (si hay déficit grave) | Mover completo otra vez como acción normal |
| Equipo único con déficit residual | Ampliar semanas o residual secuencial posterior | No actuar | — | Residual paralelo |
| Lote divisible con residual | Reprogramar lote residual | Ampliar semanas | — | Mover completo otra vez |
| Tipo desconocido | Ampliar semanas | Residual avanzado con advertencia | — | Residual automático |

### 5.3. Qué decide la app vs qué decide el usuario

| Decisión | Quién decide |
|---|---|
| Si hay línea compatible | App (calcula y muestra candidatos) |
| Si mover genera conflicto | App (calcula y muestra) |
| Si aplicar el movimiento | Usuario (botón explícito) |
| Si ampliar semanas tras mover | Usuario (segunda ronda) |
| Si reprogramar residual | Usuario (segunda ronda) |
| Si no actuar | Usuario |
| Ampliar automáticamente al mover | NUNCA la app |
| Dejar carga en origen | NUNCA la app |
| Resolver déficit automáticamente | NUNCA la app |

---

## 6. F7 matizado por tipo de acción (D5)

v0.3 estableció F7: *"La duración en destino depende de la capacidad disponible real del destino, no de la duración en origen."* v0.4 matiza su alcance por tipo de acción:

| Acción | Aplicación de F7 en v0.4 |
|---|---|
| Mover proyecto completo (1ª ronda) | F7 matizado: puede recalcular duración solo para acortar dentro del tramo original cuando el destino tiene más capacidad y el proyecto cabe sin ampliar semanas. F7 no autoriza alargar automáticamente. Si no cabe en menos semanas, el déficit queda vivo en destino semana a semana (Opción A). El acortamiento se muestra en vista previa; al aplicar, el movimiento se realiza con ese acortamiento. |
| Reprogramar residual (2ª ronda) | F7 aplica plenamente. La duración en destino emerge del cálculo semana a semana. C2, C3, C4 siguen vigentes. |
| Ampliar semanas | F7 no aplica. Es la misma línea; se extiende temporalmente. |

---

## 7. Ampliar semanas

Se mantienen todas las reglas de v0.3. Matizaciones de v0.4:

| Regla | Descripción |
|---|---|
| AMP-01 | No cambia de línea. Extiende la duración en la misma línea. |
| AMP-02 | Solo si hay semanas disponibles dentro del horizonte permitido. |
| AMP-03 | No puede combinarse con "mover completo" en la misma acción de primera ronda. |
| AMP-04 | En primera ronda: acción recomendada cuando no hay destino viable. |
| AMP-05 | En segunda ronda: acción principal para equipo único con déficit residual. |
| AMP-06 | Debe mostrar vista previa: cuántas semanas se añaden y hasta qué semana llega. |
| AMP-07 | No puede convertirse en alargamiento automático de "mover completo". |

---

## 8. Reprogramar residual

Se mantienen íntegramente las reglas de v0.3 (Sección 7, C2, C3, C4, C8, F7, F8). Matizaciones de v0.4:

| Regla | Matiz v0.4 |
|---|---|
| RES-01 | F7 aplica plenamente. La duración en destino emerge del cálculo semana a semana. |
| RES-02 | Es exclusivamente una acción de segunda ronda. No está disponible en primera ronda. |
| RES-03 | Para equipo único: inicio en semana_fin_tramo_principal + 1 (C4 de v0.3, sin cambio). |
| RES-04 | El loop de colocación aplica C3 (usar hueco libre de semana bloqueada y parar). |
| RES-05 | No es sustituto de "mover completo". Mueve el EXCESO, no el proyecto completo. |

---

## 9. Plan real y simulación activa

Sin cambios respecto a v0.3 (Sección 13). Se reafirman por completitud:

- Plan real = Excel original. No se modifica nunca.
- Simulación activa = copia de trabajo donde se aplican acciones.
- No se pierden horas entre plan real y simulación activa.
- No se duplican horas.
- No se descuenta del origen más de lo efectivamente movido a destino.
- El usuario puede descartar la simulación y volver al plan real.
- Toda acción queda trazable en columnas "En sim." y "Bloqueo".

---

## 10. Bloqueos, advertencias y recomendaciones

### 10.1. Bloqueantes de v0.3 que se mantienen

B1–B8 de v0.3 se mantienen íntegros.

### 10.2. Nuevos bloqueantes de v0.4

| Código | Situación |
|---|---|
| B9 | Mover completo + ampliar semanas seleccionados simultáneamente para el mismo proyecto |
| B10 | Texto de checkbox de transición contiene "movimiento parcial" |
| B11 | M3 deja horas del proyecto en origen tras aplicar mover completo |
| B12 | no_absorbido_h del movimiento completo regresa a origen en lugar de quedar en destino |

### 10.3. Nuevas advertencias de v0.4

| Código | Situación |
|---|---|
| A8 | Vista previa de acortamiento: "el destino tiene más capacidad disponible real; el proyecto podría completarse en menos semanas dentro del tramo original" |
| A9 | Conflicto en destino tras mover completo: "el movimiento genera déficit en destino en S[X]–S[Y]" |

---

## 11. Casos de prueba obligatorios

Los PT-01 a PT-12 de v0.3 se mantienen. Se añaden los siguientes para v0.4:

| # | Caso | Acción | Resultado esperado |
|---|---|---|---|
| PT-13 | Mover completo a destino con misma capacidad | Mover proyecto completo | Proyecto en destino con mismo patrón de semanas y mismas horas; origen = 0 h |
| PT-14 | Mover completo a destino con menos capacidad | Mover proyecto completo | Origen = 0 h; déficit vivo en destino semana a semana donde carga > cap_destino |
| PT-15 | Mover completo a destino con más capacidad | Mover proyecto completo | Destino con más capacidad → al aplicar Mover completo, el proyecto queda en destino en menos semanas dentro del tramo original; origen = 0 h; sin ampliación automática de semanas; horas conservadas |
| PT-16 | Verificar que no se amplían semanas automáticamente | Mover proyecto completo (destino con menos capacidad) | El proyecto no aparece en semanas más allá de semana_fin_actual original |
| PT-17 | Segunda ronda disponible tras déficit vivo | Mover completo (con déficit) → segunda ronda | Aparecen opciones de segunda ronda para tratar el déficit |
| PT-18 | Transición en primera semana: checkbox obligatorio | Mover completo (destino con carga en semana_inicio) | Aparece checkbox; sin marcar, botón Aplicar bloqueado |
| PT-19 | Sin checkbox marcado: no aplica | Mover completo (transición detectada, checkbox sin marcar) | Acción no se aplica; error visible |
| PT-20 | Carga de otro proyecto en destino: conflicto en destino, no en origen | Mover completo (destino con otro proyecto en semanas del movimiento) | Conflicto visible en destino; origen = 0 h |
| PT-21 | Verificar texto del checkbox | Transición detectada | El texto del checkbox no contiene "movimiento parcial" |
| PT-22 | Verificar que origen queda vacío | Mover proyecto completo (cualquier escenario) | sum(horas_proyecto_linea_origen_tras_accion) == 0 exactamente |
| PT-23 | Gantt y déficit muestran el problema en destino | Mover completo con déficit | Gantt y tabla de déficit muestran conflicto en línea destino; ninguna hora del proyecto aparece en línea origen |
| PT-24 | v0.3 intacta documentalmente | — | Los cuatro archivos v0.3 existen sin modificación; sus fechas de modificación son anteriores a v0.4 |
| PT-25 | Seleccionar "Mover proyecto completo" + "Ampliar semanas" para el mismo proyecto en la misma ronda | Mover + ampliar simultáneos | Error bloqueante; no se aplica ninguna acción; la simulación no se modifica; mensaje claro: "No se puede mover y ampliar el mismo proyecto en una sola acción. Aplica una acción y revisa la segunda ronda." |
| PT-26 | Mover completo a destino con menos capacidad — verificar ausencia de pico artificial Opción B | Mover proyecto completo | Origen = 0 h; déficit vivo aparece en destino semana a semana; no se acumula artificialmente todo el déficit en la última semana; no aparece pico final tipo Opción B; Gantt y mapa de déficit muestran el problema en las semanas reales donde ocurre |
| PT-27 | Destino con más capacidad nominal pero con carga preexistente en algunas semanas del tramo | Mover proyecto completo | El acortamiento solo se aplica si el proyecto completo cabe usando la capacidad disponible real (nominal − carga preexistente); si no cabe con capacidad disponible real, no se fuerza acortamiento; se muestra déficit vivo en destino semana a semana; no se oculta conflicto calculando con capacidad nominal |

---

## 12. Qué no debe tocarse sin aprobación

Sin cambios respecto a v0.3 (Sección 18). Se añade:

- No implementar "mover completo" antes de que los bloqueantes BL-01 a BL-07 estén cerrados y aprobados (ver Anexo v0.4).
- No implementar ninguna forma de "movimiento parcial" en la función que implementa "mover completo".
- No añadir parámetros de configuración que permitan al código elegir entre Opción A y Opción B en runtime. La decisión es Opción A; está en el documento; no en flags de código.

---

## 13. Puntos pendientes (lo que v0.4 NO cierra)

P6 queda cerrado en v0.4. Los demás pendientes de v0.3 se mantienen sin cambio. Se añade P11 como nuevo pendiente:

| ID | Pendiente | Estado |
|---|---|---|
| P1 | Nivelado de carga como mejora futura | Pendiente (sin cambio) |
| P2 | Estrategia avanzada para múltiples destinos con recálculo completo | Pendiente (sin cambio) |
| P3 | Política definitiva para semanas fuera de horizonte (> S52) | Pendiente (sin cambio) |
| P4 | Edición manual de tipo_proyecto en la UI | Pendiente (sin cambio) |
| P5 | Vista previa completa de impacto semana a semana (Fase 3) | Pendiente (sin cambio) |
| **P6** | **Mover proyecto completo con regla de exclusividad** | **CERRADO en v0.4 (Opción A)** |
| P7 | Segunda ronda con elección explícita de todas las acciones (Fase 4) | Pendiente (sin cambio) |
| P8 | "No actuar" con cuantificación exacta de horas en riesgo (Fase 10) | Pendiente (sin cambio) |
| P9 | Modo paralelo adaptado a regla de exclusividad | Pendiente (sin cambio) |
| P10 | Auditoría formal de casuísticas (Fase 8) | Pendiente (sin cambio) |
| P11 | Opción B (déficit acumulado + recálculo laminar) como variante avanzada | Nuevo pendiente v0.4 — puede implementarse en v0.5 como "Mover y recalcular duración" |

---

## 14. Tabla de compatibilidad v0.3 → v0.4

| Regla v0.3 | Cambio o ampliación v0.4 | ¿Contradice v0.3? | Cómo se resuelve |
|---|---|---|---|
| P6 pendiente: mover completo sin definir | Cerrado: Opción A, MV-01 a MV-12 | No (era pendiente explícito) | Se cierra el vacío |
| F7: recalcular duración al mover | Matizado: F7 puede acortar (no alargar) en mover completo dentro del tramo original; plenamente en residual | No (es una precisión del alcance) | Se especifica por tipo de acción |
| Checkbox de transición (v0.3 §8.4) | Texto corregido; scope clarificado | No (v0.3 no especificaba el texto) | Se cierra la ambigüedad |
| Segunda semana con otro proyecto → usar hueco y parar (C3) | C3 aplica a reprogramar residual; en mover completo con Opción A no aplica al loop | No (mover completo usa Opción A que no tiene loop C3) | Alcance separado por acción |
| B7: no saltar semanas discontinuas | Se mantiene para reprogramar residual; mover completo (Opción A) no tiene loop | No (alcance separado) | Sin contradicción |

---

*Fin del documento principal v0.4.*
