# Programación real — Reglas operativas de simulación
## Versión 0.5 — Documento vigente

**Fecha:** 2026-06-22
**Versión:** v0.5 (sustituye a v0.4)
**Estado:** Vigente. Incorpora corrección de regresión en modo secuencial y aclaraciones de textos de UI.
**Commits de referencia:** `78b9280a`, `036cb323`, `0d286768`, `ba7867f0`, `0e1db08f`, `4372f181`

---

## ÍNDICE

1. Principio fundamental: Plan real vs. Simulación activa
2. Primera ronda
3. Segunda ronda
4. Mover exceso / Reprogramar residual
5. Tipos de proyecto y comportamiento diferenciado
6. Restricciones operativas
7. Clasificación funcional de alternativas y acciones
8. Matriz de reglas
9. Cambios respecto a v0.4

---

## 1. Principio fundamental: Plan real vs. Simulación activa

### 1.1 El Plan real nunca se modifica

El Plan real es el Excel original cargado por el usuario. No se puede modificar desde la aplicación. Es la foto base contra la que se compara todo.

- Toda acción del planificador genera o actualiza una **Simulación activa**.
- La Simulación activa es una copia de trabajo acumulativa: acumula todas las acciones aplicadas en la sesión.
- Si el usuario desea descartar todos los cambios, debe usar el botón **"Reiniciar simulación"**. Al reiniciar, la Simulación activa se descarta y el Plan real vuelve a ser la base de referencia.
- Descartar la simulación no modifica el Excel ni el Plan real.

### 1.2 Simulación activa: comportamiento acumulativo

La Simulación activa se actualiza cada vez que el usuario confirma una acción. Las acciones se acumulan sobre la foto de trabajo:

- Primera acción: modifica la simulación sobre el Plan real.
- Segunda acción: modifica la simulación sobre el resultado de la primera acción.
- Cada acción queda registrada en el historial de "Acciones aplicadas".

El botón "Reiniciar simulación" es la única forma de volver al Plan real desde cero.

### 1.3 Banner de simulación activa

Cuando hay una Simulación activa en curso, la app muestra un banner informativo:

> "⚠ Simulación activa — el plan real no ha cambiado. Para descartar todos los cambios, usa el botón 'Reiniciar simulación'."

Este banner no implica que se haya cometido un error. Indica que hay cambios simulados que aún no se han descartado.

---

## 2. Primera ronda

### 2.1 Propósito

La primera ronda sirve para tomar la primera decisión sobre un proyecto que no cabe bien en su línea actual.

### 2.2 Acciones disponibles

**MV-01 — Mover proyecto completo (Solapa 1 — Mover línea)**

Mueve el proyecto completo a una o varias líneas destino.

- Mueve el proyecto en su totalidad: no mueve solo el exceso.
- Si se seleccionan varias líneas destino, la carga se reparte proporcionalmente (fracciones iguales):
  - 2 líneas destino → 50 % / 50 %
  - 3 líneas destino → aprox. 33 % / 33 % / 34 %
  - 4 líneas destino → 25 % / 25 % / 25 % / 25 %
- El reparto proporcional se aplica sobre el total de horas del proyecto.
- Preferible cuando otra línea compatible encaja mejor, porque puede evitar retrasar la entrega.

**MV-02 — Ampliar semanas (Solapa 2 — Ampliar semanas)**

Distribuye la carga del proyecto en más semanas para reducir la carga semanal.

- El proyecto ocupa más semanas → la carga por semana baja.
- Si la ampliación supera la semana de entrega objetivo, se genera aviso de impacto en entrega.
- Alternativa fuerte si no hay línea mejor o si se acepta alargar la duración.

### 2.3 Qué NO hace la primera ronda

- Mover exceso no es una acción de primera ronda en esta versión.
- No se buscan automáticamente combinaciones de movimientos de varios proyectos.
- La primera ronda actúa sobre un proyecto a la vez.

---

## 3. Segunda ronda

### 3.1 Propósito

La segunda ronda permite actuar sobre los conflictos que siguen vivos después de la primera ronda. No es una planificación nueva desde cero.

### 3.2 Entrada: qué se ve en segunda ronda

La segunda ronda trabaja exclusivamente sobre la **Simulación activa**, no sobre el Plan real. Solo muestra conflictos que siguen abiertos después de las acciones aplicadas en primera ronda.

### 3.3 Acciones disponibles en segunda ronda

| Acción | Cuándo usar |
|--------|-------------|
| **Ampliar semanas en destino** | Mantener el proyecto donde está y repartir la carga en más semanas. |
| **Mover/reprogramar exceso** | Actuar solo sobre la parte sobrante del proyecto, no sobre todo el proyecto. Ver Sección 4. |
| **No actuar** | Aceptar que ese conflicto queda vivo. El sistema registra el diagnóstico del conflicto pendiente. |

### 3.4 Combinación de acciones en segunda ronda

La segunda ronda permite combinar acciones sobre **proyectos distintos** en la misma sesión:

- Se puede ampliar semanas de un proyecto Y mover exceso de otro proyecto diferente.
- No se puede aplicar dos acciones distintas al mismo proyecto en la misma segunda ronda.

### 3.5 Mover proyecto completo en segunda ronda

Mover proyecto completo **no pertenece** a la segunda ronda como acción normal. Si el planificador necesita mover un proyecto completo después de haber aplicado acciones, debe reiniciar la simulación y replantear la primera ronda.

---

## 4. Mover exceso / Reprogramar residual

### 4.1 Qué es el exceso / residual

El exceso (también llamado residual) es la parte de la carga de un proyecto que supera la capacidad disponible en la línea origen. No es todo el proyecto: es la fracción sobrante.

### 4.2 Cómo se calcula el exceso

El exceso de un proyecto en una semana es la parte de su carga que contribuye al déficit de la línea. Dos acotaciones obligatorias:

- **No se mueve más carga que la del propio proyecto:** aunque el déficit de la línea sea grande, el exceso del proyecto no puede superar su carga real en esa semana.
- **No hay exceso si la línea no está en déficit:** el exceso es cero si la carga total de la línea no supera la capacidad nominal.

```
exceso_semana_W = min(
    carga_proyecto_en_W,
    max(0, carga_total_linea_en_W − capacidad_nominal_linea_en_W)
)
```

Donde `carga_total_linea_en_W` es la suma de las horas de todos los proyectos en esa línea y semana, y `capacidad_nominal_linea_en_W` es la capacidad disponible de la línea esa semana.

El exceso total es la suma de excesos de todas las semanas con conflicto.

### 4.3 Reparto entre destinos: fracciones proporcionales

Cuando se mueve exceso a varias líneas destino, la carga se reparte por igual entre ellas (fracciones iguales):

- 1 destino → 100 %
- 2 destinos → 50 % / 50 %
- 3 destinos → aprox. 33 % / 33 % / 34 %
- 4 destinos → 25 % / 25 % / 25 % / 25 %

**Las fracciones son independientes del modo (Paralelo/Secuencial).** La diferencia entre los dos modos es temporal, no de porcentaje.

### 4.4 Modo Paralelo

En modo Paralelo:

- El exceso se reparte entre los destinos según las fracciones.
- Cada destino recibe su fracción **en las mismas semanas donde aparece el exceso** (semanas del conflicto original).
- Ejemplo: si el exceso ocurre en S7, S8 y S9, el destino recibe carga en S7, S8 y S9.

### 4.5 Modo Secuencial

En modo Secuencial:

- El exceso se reparte entre los destinos con las **mismas fracciones** que en Paralelo (50/50, 33/33, etc.).
- La diferencia es **temporal**: cada destino recibe su fracción **después del tramo principal del proyecto en origen**, en cascada temporal.
- Regla de inicio: `semana_inicio_residual = max(semanas_del_proyecto) + 1`
- Cascada entre destinos: el segundo destino empieza donde terminó el primero.

```
Destino 1: empieza en max(semanas_proyecto) + 1
Destino 2: empieza donde terminó el Destino 1
Destino 3: empieza donde terminó el Destino 2
```

**La diferencia entre Paralelo y Secuencial es temporal, no de porcentaje.** Ambos modos reparten la misma cantidad de horas entre los mismos destinos. Solo cambia cuándo se coloca esa carga.

### 4.6 Regla de exclusividad de línea

Una línea no monta dos proyectos/modelos distintos al mismo tiempo. Esta regla distingue:

- **Carga del mismo proyecto en la línea destino:** no bloquea. Se puede usar la capacidad restante: `capacidad nominal − carga existente del mismo proyecto`.
- **Carga de otro proyecto/modelo distinto:** bloquea la semana. El cálculo se detiene al encontrar la primera semana bloqueada.

### 4.7 Capacidad utilizable por tipo de semana

| Situación de la semana W en la línea destino | Capacidad utilizable | Comportamiento |
|---|---|---|
| Vacía (sin carga) | Capacidad nominal completa | Continúa a la semana siguiente |
| Con carga del mismo proyecto | `Capacidad nominal − carga existente del mismo proyecto` | Continúa usando el hueco |
| Con carga de otro proyecto/modelo (primera semana de transición) | `Capacidad nominal − carga otro proyecto` | Se usa el hueco; requiere confirmación explícita (vista previa: "semana de transición con carga previa") |
| Con carga de otro proyecto/modelo (segunda semana en adelante) | `Capacidad nominal − carga otro proyecto` (solo la capacidad libre) | **Regla C3:** se coloca `min(pendiente, capacidad_libre)` y se detiene. No se salta a semanas posteriores. Carga no absorbida se registra con causa "línea ocupada por otro proyecto". |
| Capacidad restante = 0 (por cualquier causa) | 0 h | **Saturada:** cálculo se detiene. Carga no absorbida se registra con causa "saturación". |

**Nota sobre la regla C3:** la primera semana bloqueada (segunda en adelante con carga de otro proyecto) no se salta directamente. Se coloca lo que cabe en el hueco libre de esa semana y luego se detiene. Esto distingue dos subcasos:
- Si la semana bloqueada tiene capacidad libre → se usa esa capacidad y se detiene.
- Si la semana bloqueada está saturada (capacidad_libre = 0) → no se coloca nada y se detiene.

En ningún caso se salta esa semana para buscar huecos en semanas posteriores.

### 4.8 Información de diagnóstico al bloquearse

Cuando la colocación se detiene, la app registra y muestra:

| Campo | Descripción |
|---|---|
| Semana de bloqueo | La semana donde se detuvo la colocación |
| Causa | "línea ocupada por otro proyecto" o "saturación" |
| Proyecto/modelo bloqueante | El proyecto o modelo que ocupa la línea en esa semana |
| Capacidad libre usada | Las horas colocadas en esa semana bloqueada (0 si no había hueco) |
| Carga colocada total | Suma de horas colocadas hasta el bloqueo |
| Carga no absorbida | Horas que quedaron sin colocar |

La carga no absorbida no se pierde silenciosamente: queda registrada y visible para el usuario.

### 4.9 No buscar huecos discontinuos

El cálculo avanza por semanas consecutivas. Si la colocación se detiene (por bloqueo o saturación), el sistema no salta esa semana para buscar huecos posteriores.

- Las horas no absorbidas quedan registradas.
- No se activa automáticamente la búsqueda de otra línea.
- El planificador decide si actuar sobre el residual no absorbido.

---

## 5. Tipos de proyecto y comportamiento diferenciado

### 5.1 Equipo único

Un equipo único es un armario, inversor, convertidor u otro equipo físico que se monta como una unidad indivisible. No puede estar siendo montado en dos líneas al mismo tiempo.

**Consecuencia en modo Secuencial:** el residual siempre empieza en `max(semanas_proyecto) + 1`. El equipo termina su tramo principal antes de iniciar en el destino. Esta es la regla correcta para equipo único porque garantiza que no hay solapamiento temporal en dos líneas.

**Consecuencia en modo Paralelo para equipo único:** físicamente dudoso. La app muestra un aviso fuerte cuando se intenta aplicar modo Paralelo a un equipo único. El planificador debe confirmar explícitamente.

### 5.2 Lote divisible

Un lote divisible son varias unidades independientes dentro del mismo proyecto. Puede tener sentido repartir trabajo entre líneas simultáneamente.

**Modo Paralelo:** puede ser apropiado para lotes divisibles. El exceso se reparte entre destinos en las mismas semanas del conflicto. Cada destino recibe su fracción con las fracciones proporcionales estándar.

**Modo Secuencial:** también disponible. El exceso se reparte igual (50/50, 33/33, etc.) pero se coloca después del tramo principal, en cascada temporal. La diferencia con Paralelo es temporal, no de porcentaje.

### 5.3 Fase transferible

Solo puede moverse si esa fase puede ejecutarse realmente en otra línea. No basta compatibilidad general del modelo; debe ser compatible la fase concreta.

### 5.4 Tipo desconocido

Si el tipo de proyecto no está informado:
- No se asume que es divisible.
- No se asume que puede ir en paralelo.
- La app muestra advertencia fuerte.
- El planificador debe validar explícitamente antes de aplicar.

### 5.5 Regla de semana de inicio por tipo (modo Secuencial)

**Regla v0.5 — aplica a TODOS los tipos de proyecto en modo Secuencial:**

```
semana_inicio_residual = max(semanas_del_proyecto) + 1
```

Esta regla es uniforme para todos los tipos. La distinción por tipo de proyecto se aplica en las advertencias y validaciones, pero la semana de inicio del residual en modo secuencial siempre es `max + 1`.

**Nota histórica:** en versiones anteriores (v0.3 y una regresión de commit `95de844f`) se usaba `min(semanas_afectadas)` para los tipos lote_divisible, fase_transferible y desconocido. Esto hacía que el modo Secuencial se comportara visualmente igual que el modo Paralelo. La regla correcta y vigente es `max + 1` para todos los tipos (commit `0e1db08f`).

---

## 6. Restricciones operativas

### 6.1 Lo que no se modifica

- **Plan real:** nunca. Es la foto base. Solo se puede descartar la simulación para volver al plan real.
- **engine.py:** nunca se modifica salvo error demostrado y aprobado explícitamente.
- **Gantt de Plan real:** no se toca en acciones de simulación.
- **Resultados, Planificación, Simulación anual, Configuración, base de datos:** fuera del alcance de Programación real.

### 6.2 Lo que la simulación NO hace

- No aplica cambios automáticos sin confirmación del usuario.
- No busca combinaciones de movimientos de varios proyectos.
- No busca automáticamente otra línea si el bloqueo es definitivo.
- No pierde horas silenciosamente (toda carga no absorbida se registra).
- No modifica el Excel original.

### 6.3 Columnas de estado

| Columna | Descripción |
|---|---|
| `En sim.` | Indica si ese proyecto ya tiene acciones aplicadas en la simulación activa. |
| `Bloqueo` | Indica si la acción sobre ese proyecto está bloqueada (ya se aplicó, o hay restricción). |

---

## 7. Clasificación funcional de alternativas y acciones

### 7.1 Propósito de la clasificación

Cuando el sistema evalúa alternativas candidatas o el planificador revisa acciones en segunda ronda, las opciones deben clasificarse con una de estas cuatro categorías. Esta clasificación permite al planificador distinguir con rapidez qué puede aplicar directamente, qué debe revisar con más atención y qué no debe usar.

### 7.2 Definiciones

| Clasificación | Significado |
|---|---|
| **Directa** | Alternativa aplicable sin bloqueo relevante: la línea destino tiene compatibilidad y capacidad suficiente, y no hay restricción operativa que impida el movimiento. Se puede aplicar con confirmación estándar. |
| **Revisar** | Alternativa que puede mejorar el conflicto pero no lo resuelve completamente, o que requiere validación operativa adicional. Puede reducir el déficit pero dejar conflicto vivo. Puede pasar a segunda ronda. |
| **Bloqueada** | Alternativa que no debe aplicarse como solución directa: no hay capacidad suficiente en la línea destino, hay incompatibilidad de modelo o línea, o existe bloqueo operativo. El sistema no la descarta silenciosamente: muestra el motivo. |
| **No aplicable** | Acción o alternativa que no es adecuada para ese caso concreto, dado el tipo de proyecto, la semana, la línea o el estado de la simulación. |

### 7.3 Aclaraciones clave

- **"Revisar" no es solución cerrada.** Una alternativa clasificada como "Revisar" puede mejorar el déficit, pero el planificador debe verificar que el conflicto residual es aceptable o gestionarlo en segunda ronda.
- **"Bloqueada" no significa invisible.** El sistema muestra la alternativa bloqueada con el motivo del bloqueo, para que el planificador entienda por qué no puede usarla.
- **La clasificación es orientativa.** El planificador siempre tiene la decisión final. El sistema no impide aplicar una acción clasificada como "Revisar", pero sí advierte de los riesgos.
- **Una acción puede cambiar de categoría** si cambia el estado de la simulación (por ejemplo, al aplicar una primera ronda, una alternativa que antes era "Bloqueada" puede pasar a "Revisar").

---

## 8. Matriz de reglas

| Código | Regla | Versión de entrada |
|---|---|---|
| MV-01 | Plan real nunca se modifica | v0.1 |
| MV-02 | Simulación activa es acumulativa | v0.1 |
| MV-03 | "Reiniciar simulación" descarta todos los cambios | v0.4 |
| MV-04 | Primera ronda: mover completo o ampliar semanas | v0.1 |
| MV-05 | Mover exceso no es acción normal de primera ronda | v0.2 |
| MV-06 | Fracciones iguales entre destinos (50/50, 33/33...) | v0.2 |
| MV-07 | Paralelo: mismas semanas que el conflicto | v0.2 |
| MV-08 | Secuencial: después de `max(semanas) + 1`, cascada temporal | v0.5 (corregido) |
| MV-09 | La diferencia entre Paralelo y Secuencial es temporal, no de porcentaje | v0.5 (aclarado) |
| MV-10 | Exclusividad de línea: carga de otro proyecto bloquea | v0.3 |
| MV-11 | Carga del mismo proyecto en destino no bloquea por exclusividad | v0.3 |
| MV-12 | Semana de transición requiere confirmación explícita | v0.3 |
| MV-13 | No buscar huecos discontinuos | v0.3 |
| MV-14 | Carga no absorbida siempre se registra | v0.3 |
| MV-15 | Segunda ronda combina acciones sobre proyectos distintos | v0.4 |
| MV-16 | `max(semanas) + 1` aplica a TODOS los tipos en secuencial | v0.5 (corrección de regresión) |
| MV-17 | Semana bloqueada (2ª en adelante): usar capacidad libre antes de detener (regla C3) | v0.3 / confirmado en v0.5 |
| MV-18 | Clasificación Directa/Revisar/Bloqueada/No aplicable para alternativas y acciones | v0.5 (normativa) |

---

## 9. Cambios respecto a v0.4

### 8.1 Corrección de regresión (commit `0e1db08f`)

**Regresión detectada:** en commit `95de844f` se introdujo una diferencia en `_sem_cursor` por tipo de proyecto:

```python
# Código con regresión (NO vigente):
if tipo_proyecto == "equipo_unico":
    _sem_cursor = max(_semanas) + 1
else:
    _sem_cursor = min(_semanas_afectadas)  # ← INCORRECTO
```

Esta lógica hacía que los tipos lote_divisible, fase_transferible y desconocido en modo Secuencial empezaran en `min(semanas_afectadas)`, que es la misma semana que usa el modo Paralelo. El resultado visual era que el modo Secuencial se comportaba igual que el modo Paralelo para esos tipos.

**Corrección (vigente en v0.5):**

```python
# Código correcto (vigente):
_sem_cursor = max(_semanas) + 1
```

Esta regla aplica a todos los tipos de proyecto. El modo Secuencial siempre coloca el residual después del tramo principal del proyecto, independientemente del tipo.

### 8.2 Aclaraciones de textos de UI (commit `4372f181`)

Se actualizaron tres textos de interfaz que describían incorrectamente el comportamiento:

**Radio Paralelo/Secuencial (ayuda):**
> "Paralelo: el exceso se reparte entre las líneas destino y se coloca en las mismas semanas del conflicto. Secuencial: el exceso se reparte igual, pero se coloca después del tramo principal del proyecto, en cascada temporal entre destinos. La diferencia es temporal, no de porcentaje."

**Orientación para lote divisible:**
> "Paralelo: el exceso se reparte entre destinos en las mismas semanas del conflicto. Secuencial: el exceso se reparte igual, pero se coloca después del tramo principal del proyecto, en cascada temporal entre destinos."

**Banner de simulación activa:**
> "⚠ Simulación activa — el plan real no ha cambiado. Para descartar todos los cambios, usa el botón 'Reiniciar simulación'."

---

*Fin del documento — Reglas operativas de simulación v0.5*
