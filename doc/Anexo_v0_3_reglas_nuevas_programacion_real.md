# Anexo v0.3 — Reglas nuevas incorporadas respecto a v0.2
## Programación real · Reglas operativas de simulación

---

**Fecha:** 2026-06-21  
**Versión base:** v0.2  
**Versión resultante:** v0.3  
**Carácter:** Solo lo nuevo o aclarado en v0.3. Lo que no aparece aquí no ha cambiado respecto a v0.2.

---

## A. Nuevas reglas de v0.3

### A.1 — Duración adaptada a capacidad destino (F7)

**Qué dice v0.3:**
Cuando se mueve carga a una línea destino, la app no debe copiar automáticamente el número de semanas del origen. La duración en destino se recalcula según la capacidad disponible real del destino, semana a semana.

**Principio orientativo (no fórmula de cálculo):**

> A más horas a mover o menos capacidad libre en destino, más semanas serán necesarias. Pero esta es una estimación cualitativa. **La regla real es:** la colocación se calcula semana a semana, de forma consecutiva, usando la capacidad disponible real de cada semana; la duración resultante emerge de ese proceso — no hay una división global que la predetermina.

**Consecuencias:**
- Si el destino tiene más capacidad disponible → menos semanas → adelanto visible antes de aplicar.
- Si el destino tiene menos capacidad disponible → más semanas → retraso visible antes de aplicar.
- Ambas situaciones deben mostrarse al usuario antes de confirmar.

**Lo que cambia respecto a v0.2:** v0.2 no especificaba cómo calcular la duración en destino. v0.3 cierra ese vacío.

**Referencia Plan V05:** Fase 2 pendiente; decisiones funcionales §3 tabla "Acortar duración" / "Alargar duración".

---

### A.2 — No buscar huecos discontinuos (F8)

**Qué dice v0.3:**
La colocación avanza por semanas consecutivas desde la semana de inicio calculada. Si aparece una semana con otro proyecto/modelo, la app puede usar la capacidad libre que quede en esa semana y luego para. No salta esa semana para buscar huecos libres posteriores.

**Regla explícita:**
```
Para cada semana W desde semana_inicio en adelante:
  1. Calcular capacidad_libre = nominal − carga_otro − carga_mismo
  2. Colocar min(pendiente, capacidad_libre)
  3. Si la semana tenía otro proyecto/modelo (desde la 2ª semana del movimiento):
     → colocar lo que cabe → registrar causa → PARAR
  4. Si no había bloqueo: continuar a W+1
```

**Ejemplo:**
- 300 h a mover. Capacidad nominal 100 h/sem.
- S13: 100 h libres → coloca 100 h
- S14: 100 h libres → coloca 100 h
- S15: 60 h de otro proyecto → 40 h libres → coloca 40 h → **PARA**
- S16, S17: no se usan
- No absorbido: 60 h

**Lo que cambia respecto a v0.2:** v0.2 mencionaba implícitamente no buscar huecos. v0.3 lo hace regla explícita con comportamiento detallado para la semana de bloqueo.

**Referencia Plan V05:** §6.2, condición de aceptación Fase 1.

---

### A.3 — Usar hueco libre de la primera semana bloqueada y parar (C3)

**Qué dice v0.3:**
Cuando la colocación encuentra (desde la segunda semana del movimiento) una semana ocupada por otro proyecto/modelo con capacidad parcial disponible, la app debe:
1. Calcular `capacidad_libre = nominal − carga_otro − carga_mismo`.
2. Colocar `min(pendiente, capacidad_libre)` horas en esa semana.
3. Detener la colocación.
4. Registrar las horas no absorbidas con la causa.

**Lo que cambia respecto a v0.2 (y respecto al código anterior al commit 95de844f):**
El comportamiento anterior paraba la colocación sin usar la capacidad libre de la semana bloqueada. v0.3 establece que hay que usar lo que cabe antes de parar.

**Relación con Plan V05:** La v0.3 no contradice el Plan V05 CIERRE; lo concreta. El Plan V05 §6.2 no especificaba el comportamiento para semanas con carga parcial de otro proyecto. **v0.3 prevalece sobre V05** en este matiz: antes de detenerse, la app debe usar la capacidad libre de la primera semana bloqueada y después parar.

---

### A.4 — Equipo único: residual permitido si es secuencial y posterior (C4)

**Qué dice v0.3:**
Un equipo único no puede aparecer en dos líneas al mismo tiempo. Esto implica:
- El residual no puede colocarse en las mismas semanas que el tramo principal (paralelo = incumple F1).
- "Reprogramar residual" **sí está disponible** para equipo único.
- La acción **no se bloquea** por ser equipo único.
- El residual debe empezar en `semana_fin_tramo_principal + 1`.

**Regla de semana de inicio por tipo de proyecto:**

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

**Ejemplo obligatorio:**

| Situación | Resultado |
|---|---|
| PRY-001 en N1-L12 de S5 a S12; residual a N1-L14 | **Correcto:** empieza en S13 |
| PRY-001 en N1-L12 de S5 a S12; residual a N1-L14 | **Incorrecto:** empieza en S5 |

**Lo que cambia respecto a v0.2:** v0.2 decía "Bloqueada o no recomendada salvo validación expresa". v0.3 aclara que la validación expresa es la propia regla secuencial: si el residual empieza después del tramo principal, la acción es válida y no debe bloquearse.

---

### A.5 — Semana al 100% = saturación alta, no déficit (C5, F9)

**Qué dice v0.3:**
Una semana donde la carga usada es igual a la capacidad nominal está al 100% de uso. Eso es **saturación alta**, no déficit.

| Carga en semana W | Interpretación |
|---|---|
| < Capacidad nominal | Capacidad libre disponible |
| = Capacidad nominal | Saturación alta (al 100%) — sin déficit |
| > Capacidad nominal | **Déficit** — se supera la capacidad |

**Lo que cambia respecto a v0.2:** v0.2 no aclaraba explícitamente esta distinción. v0.3 la fija para evitar que una semana saturada se presente como problemática cuando en realidad solo está llena.

---

### A.6 — Tipo desconocido: no divisible ni paralelo por defecto (C6)

**Qué dice v0.3:**
Si el tipo de proyecto es desconocido (porque no se ha registrado en Excel o UI):
- No se asume que es divisible.
- No se asume que puede ir en paralelo.
- No se recomienda residual por defecto.
- Puede tratarse como acción avanzada con advertencia fuerte y confirmación explícita.

**Lo que cambia respecto a v0.2:** v0.2 ya lo mencionaba. v0.3 lo hace explícito en el contexto del residual de segunda ronda y la distinción por tipos.

---

### A.7 — Nivelado de carga: no es la regla base (C7)

**Qué dice v0.3:**
La regla base no es distribuir la carga uniformemente entre semanas para que todas queden al mismo nivel de ocupación. La regla base es absorber carga disponible sin superar la capacidad nominal, avanzando semana a semana desde el inicio.

El nivelado de carga queda como posible mejora futura, no como regla base de v0.3.

**Lo que cambia respecto a v0.2:** v0.2 no mencionaba explícitamente el nivelado. v0.3 lo descarta como comportamiento por defecto para evitar complejidad no aprobada.

---

### A.8 — Lote divisible: confirmación del paralelo (C8)

**Qué confirma v0.3:**
Un lote divisible puede ir en paralelo si:
- El tipo de proyecto lo permite (`permite_paralelo = sí`).
- Las líneas destino son compatibles.
- Cada línea destino recalcula su duración según su capacidad disponible real.

Si se usan varias líneas destino, debe quedar claro:
- Qué parte absorbe cada destino.
- Qué queda pendiente en total.

**Lo que añade v0.3 respecto a v0.2:** La confirmación explícita del recálculo de duración por destino.

---

### A.9 — Exclusividad: mismo proyecto/modelo, no solo mismo proyecto (nueva en v0.3)

**Qué dice v0.3:**
Cuando el Excel distingue modelo, familia o equipo dentro de un mismo proyecto, la exclusividad de línea debe considerar también ese dato. **Mismo código de proyecto no basta por sí solo** si el modelo/familia/equipo es distinto.

- Si el mismo código de proyecto cubre modelos distintos, la carga de un modelo diferente debe tratarse como "otro proyecto/modelo" a efectos de exclusividad.
- La app utiliza el campo `Modelo / familia` (o `Equipo / modelo` como fallback) para resolver esta distinción.
- Si ninguno de los dos campos está informado, la exclusividad se aplica solo por proyecto.

**Lo que añade v0.3:** Cierra el vacío de v0.2 que hablaba solo de "mismo proyecto".

---

## B. Información de diagnóstico obligatoria en bloqueos

Cuando la colocación se detiene por bloqueo, la app debe registrar y mostrar:

| Campo | Descripción |
|---|---|
| Semana de bloqueo | La semana donde se detuvo la colocación |
| Causa | "línea ocupada por otro proyecto" o "saturación" |
| Proyecto/modelo bloqueante | El proyecto o modelo que ocupa la línea en esa semana |
| Capacidad libre usada | Las horas colocadas en esa semana bloqueada (0 si no había hueco) |
| Carga colocada total | Suma de horas colocadas hasta el bloqueo |
| Carga no absorbida | Horas que quedaron sin colocar |

---

## C. Reglas que NO cambian respecto a v0.2

Las siguientes reglas de v0.2 se mantienen íntegramente:

- Plan real = Excel original, no se modifica nunca.
- Simulación activa = copia de trabajo.
- No se pierden ni se duplican horas.
- No se descuenta del origen más de lo colocado en destino.
- Primera ronda: mover completo primero si encaja mejor.
- Ampliar semanas: segunda opción fuerte.
- Residual no es acción normal de primera ronda.
- Primera semana con otro proyecto = semana de transición (requiere confirmación explícita).
- No se busca automáticamente otra línea si el bloqueo es definitivo.
- "No actuar" siempre disponible con diagnóstico.
- Columnas "En sim." y "Bloqueo" funcionando.
- engine.py no se toca salvo necesidad demostrada.

---

## D. Trazabilidad no normativa

*Esta sección registra el estado de implementación en código. No es normativa. Los cambios de estado no alteran las reglas anteriores.*

| Regla | Estado en código | Commit |
|---|---|---|
| A.1 — Duración adaptada a capacidad destino | Calculada en motor; preview completo pendiente (Fase 3) | — |
| A.2 — No buscar huecos discontinuos | Implementado: bloqueo detiene el while loop | ba7867f0 |
| A.3 — Usar hueco libre antes de parar | **Pendiente de hotfix** | — |
| A.4 — Equipo único: inicio en semana_fin + 1 | Implementado | 95de844f |
| A.5 — Saturación 100% vs. déficit | Lógica correcta en motor; texto de UI pendiente de aclarar | — |
| A.6 — Tipo desconocido: no divisible | Implementado (warning en UI) | ba7867f0 |
| A.7 — No nivelar | No cambio de código; es una aclaración de intención | — |
| A.8 — Lote divisible paralelo | Implementado (modo paralelo existente) | — |
| A.9 — Mismo proyecto/modelo | Implementado (`_modelo_col` fallback chain) | ba7867f0 |

---

*Fin del Anexo v0.3.*
