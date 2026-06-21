# PROGRAMACIÓN REAL
## Reglas operativas de simulación
### v0.3 — Fuente de verdad funcional antes de tocar código

---

**Estado:** v0.3 vigente  
**Fecha:** 2026-06-21  
**Sustituye:** v0.2 (2026-06-20)  
**Documento base:** Reglas operativas v0.2 + Plan de implementación V05 CIERRE + decisiones funcionales validadas en sesión 2026-06-21  

> **Qué es este documento:** Evolución ordenada de v0.2. No elimina las reglas anteriores: las confirma, amplía o aclara. Lo que no aparece como cambiado se mantiene igual que en v0.2.
>
> **Qué no es:** No es una especificación de código ni una autorización para modificar app.py o engine.py.

---

## 1. Qué cambia respecto a v0.2

| ID | Área | Naturaleza del cambio |
|---|---|---|
| C1 | Duración en destino | Nueva regla: recalcular semanas según capacidad real; no copiar duración del origen |
| C2 | Colocación secuencial | Nueva regla: no buscar huecos discontinuos; avanzar semana a semana y parar al bloquear |
| C3 | Semana bloqueada con hueco | Aclaración: la app puede usar la capacidad libre antes de parar (no bloquear sin colocar nada) |
| C4 | Equipo único | Aclaración: no se bloquea "Reprogramar residual"; sí se exige que sea secuencial y posterior al tramo principal |
| C5 | Saturación al 100% | Aclaración: semana al 100% = saturación alta, no déficit |
| C6 | Tipo desconocido | Aclaración: no se asume divisible ni paralelo |
| C7 | Nivelado de carga | Aclaración: no es la regla base; queda como mejora futura |
| C8 | Lote divisible | Confirmación: puede ir en paralelo si el tipo y las líneas lo permiten |

Ninguno de estos cambios contradice el espíritu de v0.2. Varios son aclaraciones que eliminan ambigüedad. Ver tabla de compatibilidad en Sección 16.

> **Relación con el Plan V05 CIERRE:** La v0.3 no contradice el Plan V05 CIERRE; lo concreta. En el matiz de bloqueo temporal en destino, **v0.3 prevalece sobre V05**: antes de detenerse, la app debe usar la capacidad libre de la primera semana bloqueada por otro proyecto/modelo y después parar. El Plan V05 §6.2 no especificaba este comportamiento para semanas con carga parcial de otro proyecto; v0.3 lo cierra explícitamente.

---

## 2. Objetivo y alcance

### 2.1. Objetivo operativo

- Definir cuándo una alternativa simulable debe aparecer como recomendada, permitida, no recomendada, avanzada o bloqueada.
- Evitar que la app proponga acciones matemáticamente válidas pero industrialmente dudosas.
- Distinguir entre equipo único, lote divisible, fase transferible y proyecto sin clasificar.
- Separar la lógica de primera ronda y segunda ronda.
- Establecer cómo se calcula la duración real en destino.
- Cerrar la regla de colocación consecutiva sin huecos discontinuos.
- Aclarar qué significa saturación frente a déficit.

### 2.2. Contexto industrial

| Elemento | Criterio |
|---|---|
| Producto | Convertidores, inversores o armarios industriales de gran tamaño |
| Dimensiones típicas | Aprox. 3–5 m de largo, 1 m de ancho, 2,5–3 m de alto |
| Nivel de planificación | Macro semanal. No entra al detalle fino de operaciones por puesto |
| Restricción física | Un mismo equipo físico no puede montarse simultáneamente en dos líneas |
| Matiz clave | Un proyecto puede ser una unidad, varias unidades o una fase transferible |

---

## 3. Taxonomía operativa de proyecto

### 3.1. Regla madre

La acción residual no depende solo de horas. Depende de qué representa el proyecto: una unidad física, un lote de unidades o una fase físicamente transferible.

| Tipo | Descripción | ¿Divisible? | ¿Puede ir en paralelo? | Acción residual |
|---|---|---|---|---|
| Equipo único | Un solo armario, convertidor o inversor físico | No | No | Permitida solo si es secuencial y posterior al tramo principal; no en paralelo |
| Lote divisible | Varias unidades independientes del mismo proyecto | Sí, por unidades | Sí, si las líneas son compatibles | Permitida; puede repartirse como lote residual |
| Fase transferible | Una fase físicamente separable puede ejecutarse en otra línea | No por unidad; sí por fase | Depende de la fase | Permitida solo si la fase y la línea son compatibles |
| Desconocido | No hay dato suficiente en Excel o UI | Incierto | No por defecto | Acción avanzada con advertencia fuerte; nunca recomendada por defecto; no se asume divisible |

### 3.2. Campos mínimos

| Campo | Valores / uso | Carácter |
|---|---|---|
| tipo_proyecto | equipo_unico / lote_divisible / fase_transferible / desconocido | Obligatorio funcional |
| n_unidades | Número de unidades del proyecto | Informativo; no determina divisibilidad por sí solo |
| permite_reprogramacion_residual | sí / no / desconocido | Clave para condicionar residual |
| permite_paralelo | sí / no / desconocido | Clave para decidir paralelo o secuencial |

### 3.3. No inferir automáticamente

El número de unidades ayuda, pero no debe inferir por sí solo que el proyecto puede dividirse. Puede haber varias unidades no separables por utillaje, cliente, pruebas, trazabilidad o criterio operativo. Si falta tipo_proyecto, tratar como desconocido.

---

## 4. Reglas físicas y operativas

### 4.1. Reglas físicas

| Código | Regla física | Consecuencia |
|---|---|---|
| F1 | Un equipo físico único no puede estar en dos líneas a la vez | No permitir residual en paralelo para equipo único; si se permite residual, debe empezar después del tramo principal |
| F2 | Un lote de unidades sí puede repartirse | Permitir residual paralelo si el tipo y las líneas lo soportan |
| F3 | Una fase transferible exige compatibilidad específica | No basta con compatibilidad de modelo general |
| F4 | La línea destino debe ser compatible y tener capacidad definida | Bloquear si no hay capacidad o compatibilidad válida |
| F5 | Una acción que crea conflicto en destino no debe ocultarlo | Recalcular y mostrar conflicto vivo |
| F6 | Mover completo de nuevo en segunda ronda no es flujo normal | Tratarlo como acción avanzada o replanteamiento |
| **F7** | **La duración en destino depende de la capacidad disponible real del destino, no de la duración en origen** | **No copiar automáticamente el número de semanas del origen al destino** |
| **F8** | **La colocación avanza por semanas consecutivas sin saltar huecos** | **No buscar semanas libres posteriores al primer bloqueo** |
| **F9** | **Una semana al 100% de capacidad usada es saturación alta, no déficit** | **No presentar como déficit una semana que no supera la capacidad nominal** |

### 4.2. Duración resultante en destino (C1 — nueva en v0.3)

Cuando se mueve carga a otra línea, la app no debe copiar automáticamente la duración del origen. Debe recalcular semanas según la capacidad disponible real del destino.

**Principio conceptual (no fórmula de cálculo):**

> Como orientación conceptual: a más horas a mover o menos capacidad libre en destino, más semanas serán necesarias. Pero esta es una estimación cualitativa, **no la regla de cálculo**.
>
> **La regla real es:** la colocación se calcula semana a semana, de forma consecutiva, usando la capacidad disponible real de cada semana; la app se detiene ante el primer bloqueo por otro proyecto/modelo (después de usar el hueco libre de esa semana si existe). La duración resultante emerge de ese proceso — no hay una división global que la predetermina.

La duración resulta de cuántas semanas consecutivas se necesitan para absorber toda la carga, considerando:

- Capacidad nominal de la línea destino
- Carga ya existente en destino (del mismo proyecto o de otro)
- Capacidad libre real por semana
- Posibles bloqueos por exclusividad de línea

**Más capacidad → menos semanas.** Si el destino tiene más capacidad disponible que el origen, la carga puede colocarse en menos semanas. Esto es una mejora si reduce déficit y no genera conflicto mayor. Debe mostrarse el adelanto antes de aplicar.

**Menos capacidad → más semanas.** Si el destino tiene menos capacidad disponible, la carga puede necesitar más semanas. Esto puede ser válido especialmente en segunda ronda. Debe mostrarse el retraso antes de aplicar.

**No nivelar.** La regla base no es repartir la carga uniformemente para que todas las semanas queden al mismo nivel de ocupación. La regla base es absorber carga usando la capacidad disponible sin superar la capacidad nominal. El nivelado de carga queda como posible mejora futura, no como regla base de v0.3.

### 4.3. Capacidad utilizable en semana W

| Situación de la semana W en destino | Capacidad utilizable |
|---|---|
| W vacía (sin carga) | Capacidad nominal completa |
| W con carga del mismo proyecto | Capacidad nominal − carga existente del mismo proyecto |
| W con carga del mismo proyecto que agota capacidad | Cero → saturación → detener |
| Primera semana del movimiento con carga de otro proyecto/modelo (transición) | Capacidad nominal − carga del otro − carga del mismo; requiere confirmación explícita |
| Segunda semana o posterior con carga de otro proyecto/modelo | Capacidad nominal − carga del otro − carga del mismo → colocar lo que cabe → detener (v0.3) |
| Cualquier semana con capacidad cero (cualquier causa) | Cero → saturación → detener |

> **Matiz — "mismo proyecto" vs. "mismo proyecto/modelo":** En la práctica, cuando el Excel distingue modelo, familia o equipo dentro de un mismo proyecto, la exclusividad debe considerar también ese dato. **Mismo código de proyecto no basta por sí solo** si el modelo/familia/equipo es distinto. Si el mismo código de proyecto cubre modelos distintos, la carga de un modelo diferente debe tratarse como "otro proyecto/modelo" a efectos de exclusividad de línea. La app utiliza el campo `Modelo / familia` (o `Equipo / modelo` como fallback) para resolver esta distinción.

---

## 5. Primera ronda: lógica de decisión

### 5.1. Pregunta de primera ronda

El proyecto, tal como está en el plan real, no cabe. ¿Existe una línea compatible donde el proyecto completo encaje mejor?

| Situación | Acción recomendada | Permitida | No recomendada / bloqueada |
|---|---|---|---|
| Hay línea compatible y encaja mejor | Mover proyecto completo | Ampliar semanas | Residual en primera ronda |
| No hay destino compatible | Ampliar semanas | No actuar | Mover a incompatible |
| Destino compatible pero genera conflicto | Mover completo con advertencia | Ampliar semanas | Ocultar conflicto |
| Equipo único | Mover completo o ampliar | No actuar | Residual paralelo |
| Lote divisible | Mover completo | Ampliar / residual si procede | Paralelo sin control |
| Tipo desconocido | Mover completo o ampliar | Residual avanzado con advertencia | Residual recomendado |

### 5.2. Árbol de primera ronda

1. Buscar línea compatible donde el proyecto completo encaje mejor.
2. Si existe y no crea conflicto grave: recomendar mover proyecto completo.
3. Si no existe línea viable: recomendar ampliar semanas si el plazo y horizonte lo permiten.
4. Si no hay línea ni margen temporal: mostrar "No actuar" con diagnóstico de bloqueo.
5. No abrir residual como acción normal de primera ronda.

---

## 6. Segunda ronda: lógica de decisión

### 6.1. Pregunta de segunda ronda

Ya se aplicó una primera acción. Si sigue habiendo conflicto, ¿qué ajuste tiene sentido sin convertir la simulación en una cadena errática de movimientos?

| Situación | Acción recomendada | Permitida | No recomendada / bloqueada |
|---|---|---|---|
| Déficit residual y ampliar no genera bloqueo | Ampliar semanas | No actuar | Residual si desconocido |
| Equipo único con déficit residual | Ampliar semanas o residual secuencial posterior | No actuar | Residual paralelo; residual en mismas semanas del tramo principal |
| Lote divisible con residual | Reprogramar lote residual | Ampliar semanas | Mover completo otra vez |
| Fase transferible | Reprogramar tramo/fase residual | Ampliar semanas | Mover completo si no hace falta |
| Tipo desconocido | Ampliar semanas | Residual avanzado con advertencia | Residual recomendado |
| Destino se satura tras acción | Mostrar conflicto vivo | Aplicar bajo criterio | Ocultar conflicto |

### 6.2. Residual en segunda ronda

| Tipo de proyecto | Comportamiento del residual | Estado recomendado |
|---|---|---|
| Equipo único | Solo secuencial y solo posterior al tramo principal; no en paralelo; no en las mismas semanas | Disponible como acción; advertencia; no bloqueada si es secuencial |
| Lote divisible | Puede ir en paralelo si permite_paralelo = sí y destinos compatibles | Permitida / recomendada si resuelve conflicto |
| Fase transferible | Secuencial o paralela según fase; compatibilidad funcional específica | Permitida condicionada |
| Desconocido | No asumir divisible; advertencia fuerte; confirmación explícita | Avanzada, nunca recomendada por defecto |

---

## 7. Reprogramar residual

### 7.1. Regla de equipo único (C4 — aclarada en v0.3)

Un equipo único no puede estar en dos líneas al mismo tiempo. Por tanto:

- El residual **no puede colocarse en paralelo** al tramo principal.
- "Reprogramar residual" **sí está disponible** para equipo único si la ejecución es secuencial.
- **No se bloquea la acción** por ser equipo único. Se ajusta la semana de inicio.
- El residual debe empezar en la semana posterior al fin del tramo principal ya colocado.

**Ejemplo obligatorio:**

> PRY-001 está en N1-L12 de S5 a S12.  
> Si se reprograma residual a N1-L14:
> - **Correcto:** el residual empieza en S13.
> - **Incorrecto:** el residual empieza en S5 (paralelismo físicamente imposible).

**Regla funcional de semana de inicio — por tipo de proyecto:**

```
Si tipo_proyecto == "equipo_unico":
    semana_inicio_residual = semana_fin_tramo_principal + 1
    (el equipo no puede estar en dos líneas simultáneamente)

Si tipo_proyecto == "lote_divisible":
    semana_inicio_residual = primera semana con exceso vivo
    (puede ir en paralelo si permite_paralelo = sí y las líneas son compatibles)

Si tipo_proyecto == "fase_transferible":
    semana_inicio_residual = primera semana con exceso vivo
    (solo si la fase concreta es compatible con la línea destino;
     no basta con compatibilidad general del modelo)

Si tipo_proyecto == "desconocido" o vacío/no informado:
    → tratar como desconocido
    → no se asume divisible ni paralelo
    → solo acción avanzada con advertencia fuerte y validación explícita
    → semana_inicio_residual = primera semana con exceso vivo
      (únicamente si el usuario valida explícitamente que procede)
```

### 7.2. Regla de lote divisible (C8 — confirmada en v0.3)

- Puede ir en paralelo si el tipo y las líneas lo permiten.
- Puede repartirse por unidades o sublotes.
- Cada línea destino recalcula su duración según su capacidad disponible real.
- Si se usan varias líneas destino, debe quedar claro qué parte absorbe cada destino y qué queda pendiente.
- La semana de inicio es la primera semana con exceso vivo.

### 7.3. Regla de fase transferible

- Solo puede moverse si esa **fase concreta** es compatible con la línea destino — en términos de proceso, utillaje y certificaciones requeridas, no solo en términos del modelo general.
- No basta con que el modelo sea compatible si la fase específica no lo es.
- La validación de compatibilidad de fase debe hacerse antes de abrir la opción de residual.
- Si la compatibilidad de fase no está documentada, tratar como tipo desconocido (advertencia fuerte).

### 7.4. Regla de tipo desconocido

- No se asume divisible.
- No se asume paralelo.
- No se recomienda residual por defecto.
- Puede tratarse como acción avanzada con advertencia fuerte y validación explícita.

---

## 8. No buscar huecos discontinuos (C2, C3 — nuevas en v0.3)

### 8.1. Regla de colocación consecutiva

Cuando se reprograma residual en destino, la app avanza por semanas consecutivas desde la semana de inicio calculada.

**Si aparece una semana ocupada por otro proyecto/modelo:**

1. La app puede usar la capacidad libre que quede en esa semana: `capacidad nominal − carga del otro − carga del mismo proyecto`.
2. Si la capacidad libre es mayor que cero: colocar lo que cabe en esa semana.
3. Si la semana queda al 100% de capacidad usada: informarlo como saturación alta (no como déficit).
4. Si queda carga pendiente después de usar esa capacidad: queda como no absorbida.
5. **La app no debe saltar esa semana para buscar semanas libres posteriores.**
6. La colocación se detiene tras usar la capacidad disponible en la primera semana bloqueada.

### 8.2. Qué debe informar la app

Cuando se produce un bloqueo por otro proyecto/modelo:

- Semana donde se produce el bloqueo.
- Proyecto/modelo que ocupa la línea en esa semana.
- Capacidad libre usada en esa semana.
- Carga colocada hasta ese punto.
- Carga no absorbida.
- Causa del bloqueo ("línea ocupada por otro proyecto" / "saturación").

### 8.3. Ejemplo obligatorio

**Carga residual a mover: 300 h. Línea destino con capacidad nominal 100 h/sem.**

| Semana | Estado | Capacidad libre | Comportamiento correcto | Comportamiento incorrecto |
|---|---|---|---|---|
| S13 | Libre | 100 h | Coloca 100 h. Pendiente: 200 h | — |
| S14 | Libre | 100 h | Coloca 100 h. Pendiente: 100 h | — |
| S15 | Otro proyecto (60 h) | 40 h | Coloca 40 h. Pendiente: 60 h → no absorbido. **Para.** | — |
| S16 | Libre | 100 h | **No se usa** | Coloca 60 h → incumple v0.3 |
| S17 | Libre | 100 h | **No se usa** | Coloca carga → incumple v0.3 |

**Resultado correcto:**
- S13: 100 h colocadas.
- S14: 100 h colocadas.
- S15: 40 h colocadas (capacidad disponible tras otro proyecto). Semana al 100%.
- No absorbido: 60 h.
- S16 y S17: no usadas.

### 8.4. Primera semana con otro proyecto (transición)

La primera semana del movimiento puede tratarse como semana de transición si hay carga de otro proyecto/modelo que termina. En ese caso:
- Se usa la capacidad parcial disponible.
- La vista previa debe mostrarla explícitamente como "semana de transición con carga previa".
- Requiere confirmación explícita del usuario antes de aplicar.
- El movimiento continúa a las semanas siguientes normalmente.

La diferencia con v0.3 (C3): desde la segunda semana con otro proyecto, se usa la capacidad disponible y se para, en lugar de parar sin usar nada.

---

## 9. Carga no absorbida

Si no cabe todo:

- Se coloca lo que cabe según la capacidad disponible.
- Se informa lo no absorbido con la causa exacta.
- Se mantiene conflicto vivo: no se presenta como solucionado.
- No se oculta saturación en destino.
- No se pierde ni se duplica ninguna hora.
- No se descuenta del origen más de lo efectivamente colocado en destino.

**Causas de carga no absorbida:**

| Causa | Descripción |
|---|---|
| Saturación | La capacidad nominal está agotada (cualquier combinación de cargas) |
| Línea ocupada por otro proyecto | Se usó la capacidad parcial disponible y quedó pendiente tras la primera semana bloqueada |
| Capacidad cero | La línea no tiene capacidad definida o es cero |

---

## 10. Saturación vs. déficit (C5 — aclarado en v0.3)

| Situación | Interpretación correcta | Interpretación incorrecta |
|---|---|---|
| Semana con carga = capacidad nominal | **Saturación alta** (línea al 100%) | "Déficit" (no hay déficit si no se supera la capacidad) |
| Semana con carga > capacidad nominal | **Déficit** (se supera la capacidad) | Saturación (es algo más grave) |
| Semana con carga < capacidad nominal | Capacidad libre disponible | — |

Una semana al 100% de uso no es un problema de déficit: la línea está saturada pero dentro de su capacidad. Solo hay déficit cuando la carga supera la capacidad nominal.

---

## 11. Bloqueos, advertencias y recomendaciones

### 11.1. Bloqueantes

| Regla | Situación |
|---|---|
| B1 | Línea incompatible |
| B2 | Falta de simulación activa en segunda ronda |
| B3 | Pérdida de horas (no absorbidas silenciosamente) |
| B4 | Capacidad inexistente o no definida |
| B5 | Residual paralelo para equipo único |
| B6 | Mover completo de nuevo como acción normal en segunda ronda |
| B7 | Saltar semanas bloqueadas para buscar huecos discontinuos |
| B8 | Colocar residual de equipo único en semanas del tramo principal |

### 11.2. Advertencias fuertes

| Regla | Situación |
|---|---|
| A1 | Tipo desconocido |
| A2 | Destino se satura tras la acción |
| A3 | Proyecto ya movido en primera ronda |
| A4 | Acción genera semanas fuera de horizonte |
| A5 | Residual sin confirmación de divisibilidad |
| A6 | Semana de transición (primera semana con carga de otro proyecto) |
| A7 | Equipo único con residual: "esta acción es secuencial y posterior al tramo principal" |

### 11.3. Recomendaciones

- Mover completo en primera ronda si encaja mejor.
- Ampliar en segunda ronda si resuelve sin bloqueo.
- Residual solo para lote divisible, fase transferible o validación expresa.
- Para equipo único: ampliar semanas es la primera opción; residual secuencial posterior es la segunda.

---

## 12. "No actuar" y casos límite

### 12.1. "No actuar" no es silencio

Cuando no hay alternativa buena, la app debe decir por qué. "No actuar" debe ser una decisión informada con diagnóstico:

| Caso | Comportamiento v0.3 |
|---|---|
| No hay línea compatible | No actuar con diagnóstico: "No existe destino compatible" |
| Ampliar excede plazo u horizonte | Advertir o bloquear según regla de plazo/horizonte |
| Residual no permitido por tipo | Mostrar como avanzado con advertencia, o informar que no está recomendado |
| Destino crea conflicto | Permitir bajo criterio; mostrar conflicto vivo |
| Falta tipo de proyecto | No recomendar residual; mostrarlo solo como avanzado con advertencia |
| Proyecto ya movido dos veces | Tratar como conflicto estructural; no seguir encadenando acciones normales |

### 12.2. Horizonte máximo

Si la colocación resultante excede S52, debe advertirse o bloquearse según la política de horizonte. Pendiente de cierre definitivo (ver Sección 15).

---

## 13. Plan real y simulación activa

- **Plan real** = Excel original cargado por el usuario. No se modifica nunca.
- **Simulación activa** = copia de trabajo donde se aplican acciones.
- Toda acción debe quedar trazable: visible en las columnas "En sim." y "Bloqueo".
- No se pierden horas entre plan real y simulación activa.
- No se duplican horas.
- No se descuenta del origen más de lo efectivamente colocado en destino.
- El usuario puede descartar la simulación y volver al plan real.

---

## 14. Clasificación final de acciones

| Contexto | Recomendada | Permitida | No recomendada | Bloqueada / futura |
|---|---|---|---|---|
| 1ª ronda: línea compatible encaja mejor | Mover completo | Ampliar | Residual | Mover incompatible |
| 1ª ronda: sin destino viable | Ampliar | No actuar | Mover | Mover incompatible |
| 2ª ronda: déficit sin bloqueo | Ampliar | No actuar | Residual si desconocido | Mover completo normal |
| Equipo único 2ª ronda | Ampliar / residual secuencial posterior | No actuar | — | Residual paralelo; residual en semanas del tramo |
| Lote divisible | Mover completo / residual | Ampliar | — | Paralelo sin control |
| Fase transferible | Residual condicionado | Ampliar | Mover completo si no hace falta | Fase incompatible |
| Tipo desconocido | Mover completo / ampliar | Residual avanzado | Residual recomendado | Residual automático |
| Destino saturado | Mostrar conflicto vivo | Aplicar bajo criterio | Ocultar conflicto | — |
| Proyecto movido varias veces | Replantear simulación | Acción avanzada | Seguir encadenando | Movimiento normal repetido |

---

## 15. Casos de prueba obligatorios

| # | Caso | Tipo proyecto | Acción | Resultado esperado |
|---|---|---|---|---|
| PT-01 | Equipo único S5–S12 en N1-L12, residual a N1-L14 | equipo_unico | Reprogramar residual secuencial | Residual empieza en S13; no en S5 |
| PT-02 | Mismo equipo, verificar conservación de horas | equipo_unico | — | Horas origen + horas destino = horas originales |
| PT-03 | Destino con más capacidad (200 h/sem) que origen (100 h/sem) | lote_divisible | Reprogramar residual secuencial | Residual ocupa menos semanas; adelanto visible |
| PT-04 | Destino con menos capacidad (50 h/sem) que origen (100 h/sem) | lote_divisible | Reprogramar residual secuencial | Residual ocupa más semanas; retraso visible |
| PT-05 | Semana bloqueada con 40 h libres (otro proyecto ocupa 60 h de 100 h/sem) | cualquiera | Reprogramar residual secuencial | Coloca 40 h en semana bloqueada; para; no usa semanas posteriores |
| PT-06 | Semana bloqueada sin ninguna h libre (otro proyecto ocupa 100 h de 100 h/sem) | cualquiera | Reprogramar residual secuencial | Para sin colocar nada; todo queda no absorbido desde esa semana |
| PT-07 | Lote divisible, residual paralelo | lote_divisible | Reprogramar residual paralelo | Se coloca en mismas semanas del conflicto; resultado sin cambios respecto a versión anterior |
| PT-08 | Tipo desconocido, residual solicitado | desconocido | Reprogramar residual | Aparece advertencia fuerte; no se recomienda automáticamente |
| PT-09 | Destino al 100% de ocupación (sin superarla) | cualquiera | — | Se muestra como saturación alta, no como déficit |
| PT-10 | Destino con carga que supera capacidad nominal | cualquiera | — | Se muestra como déficit |
| PT-11 | Plan real: verificar que no se modifica tras cualquier acción | cualquiera | Cualquiera | Excel original intacto; solo simulación activa cambia |
| PT-12 | Primera semana con otro proyecto (transición) | cualquiera secuencial | Reprogramar residual | Aparece aviso de semana de transición; requiere confirmación explícita; continúa a semanas siguientes |

---

## 16. Tabla de compatibilidad v0.2 → v0.3

| Regla v0.2 | Cambio o ampliación v0.3 | ¿Contradice v0.2? | Cómo se resuelve | Referencia Plan V05 CIERRE |
|---|---|---|---|---|
| Semana inicio del residual = primera semana de exceso vivo | Para equipo único: semana inicio = fin tramo principal + 1 | No (es un caso especial explícito) | Condición por tipo_proyecto dentro de la misma lógica | §4.1, §6.2 |
| Equipo único: residual bloqueada o no recomendada | Equipo único: residual disponible si es secuencial y posterior | No (aclara; v0.2 decía "no recomendada salvo validación") | La validación es la propia regla secuencial + poster | §2.2, §4.1, Fase 9 |
| Segunda semana con otro proyecto → bloqueo inmediato sin colocar | Segunda semana con otro proyecto → usar capacidad libre, luego parar | No (es más preciso) | Ampliar el bloqueo: usar antes de parar | §6.2, condición de aceptación Fase 1 |
| Duración en destino no especificada | Nueva regla F7: recalcular duración según capacidad real | No (cubre un vacío) | Regla nueva sin contradicción | Fase 2 pendiente |
| No buscar huecos discontinuos (mencionado implícitamente) | Regla F8 explícita: colocación consecutiva sin saltar semanas | No (explicitación) | Se hace explícita y se añade ejemplo | §6.2, Fase 1 CA |
| Saturación vs. déficit (sin aclaración) | Regla F9: 100% = saturación alta, > 100% = déficit | No (aclaración) | Terminología aclarada | §3 tabla |
| Nivelado como opción posible | Nivelado = mejora futura, no regla base | No (aclara prioridad) | Queda en pendientes | — |
| Tipo desconocido: no divisible | Confirmado + explicitado en residual | No (confirmación) | Sin cambio de fondo | §3, §6 |

---

## 17. Puntos pendientes (lo que v0.3 NO cierra)

Los siguientes puntos quedan explícitamente fuera del alcance de v0.3 y deben cerrarse en versiones posteriores con aprobación expresa:

| ID | Pendiente | Referencia |
|---|---|---|
| P1 | Nivelado de carga como mejora futura | Sección 4.2 de este documento |
| P2 | Estrategia avanzada para reparto entre múltiples destinos con recálculo completo | Plan V05 §6.4 |
| P3 | Política definitiva para semanas fuera de horizonte (> S52) | Plan V05 §8 casos límite |
| P4 | Edición manual de tipo_proyecto en la UI (hoy solo viene de Excel) | Plan V05 RF2 |
| P5 | Vista previa completa de impacto semana a semana (Fase 3 del plan) | Plan V05 Fase 3 |
| P6 | Mover proyecto completo con regla de exclusividad (Fase 2 del plan) | Plan V05 Fase 2 |
| P7 | Segunda ronda con elección explícita de todas las acciones (Fase 4 del plan) | Plan V05 Fase 4 |
| P8 | "No actuar" con cuantificación exacta de horas en riesgo (Fase 10 del plan) | Plan V05 Fase 10 |
| P9 | Modo paralelo adaptado a regla de exclusividad (requiere auditoría específica) | Plan V05 §6.3 |
| P10 | Auditoría formal de casuísticas (Fase 8 del plan) previo a cerrar Fase 9 | Plan V05 Fase 8 |

---

## 18. Qué no se debe tocar sin aprobación

- engine.py salvo necesidad demostrada y aprobación explícita.
- Cálculo central de capacidad, déficit o saturación.
- Resultados, Planificación o Simulación anual.
- Guardado/carga normal de escenarios.
- Base de datos: sin tablas nuevas ni columnas nuevas por defecto.
- Botones explícitos: no sustituir por automatismos.
- Flujos visuales ya validados: "En sim.", "Bloqueo", acciones aplicadas.
- Modo paralelo sin auditoría previa.

---

*Fin del documento principal v0.3.*
