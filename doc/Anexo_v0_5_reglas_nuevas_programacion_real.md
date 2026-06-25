# Anexo v0.5 — Reglas nuevas incorporadas respecto a v0.4
## Programación real · Reglas operativas de simulación

---

**Fecha:** 2026-06-22
**Versión base:** v0.4
**Versión resultante:** v0.5
**Carácter:** Solo lo nuevo o aclarado en v0.5. Lo que no aparece aquí no ha cambiado respecto a v0.4.
**Commits:** `0e1db08f` (corrección de regresión), `4372f181` (aclaraciones de UI)

---

## A. Nuevas reglas de v0.5

### A.1 — Modo secuencial: `max(semanas) + 1` para todos los tipos de proyecto (MV-16)

**Qué dice v0.5:**
En modo Secuencial, la semana de inicio del residual es siempre `max(semanas_del_proyecto) + 1`, para todos los tipos de proyecto (equipo único, lote divisible, fase transferible y desconocido).

**Regla:**
```
semana_inicio_residual = max(_semanas) + 1
```

Esta regla es uniforme e independiente del tipo de proyecto.

**Por qué cambia respecto a v0.4:**
En v0.4, existía una diferencia por tipo de proyecto introducida en el commit `95de844f`:

```python
# Código con regresión (NO vigente desde 0e1db08f):
if tipo_proyecto == "equipo_unico":
    _sem_cursor = max(_semanas) + 1
else:
    _sem_cursor = min(_semanas_afectadas)
```

Esta diferenciación era incorrecta: hacía que los tipos lote_divisible, fase_transferible y desconocido en modo Secuencial empezaran en `min(semanas_afectadas)`, que es la misma semana que usa el modo Paralelo. El resultado visual era que el modo Secuencial se comportaba igual que el Paralelo para esos tipos, eliminando toda diferencia funcional entre los dos modos.

**Código correcto (vigente):**
```python
_sem_cursor = max(_semanas) + 1
```

**Lo que cambia respecto a v0.4:** la corrección se aplica a los tipos lote_divisible, fase_transferible y desconocido. Para equipo_unico ya era correcta en v0.4.

**Commit:** `0e1db08f` — Fix sequential residual start for all project types

---

### A.2 — Distinción Paralelo vs Secuencial: temporal, no de porcentaje (MV-09)

**Qué dice v0.5:**
La diferencia entre el modo Paralelo y el modo Secuencial es exclusivamente **temporal**. Las fracciones de reparto (50/50, 33/33, etc.) son idénticas en ambos modos.

| Modo | Fracciones | Semana de inicio |
|---|---|---|
| Paralelo | 50/50, 33/33, 25/25... | Mismas semanas donde aparece el exceso vivo |
| Secuencial | 50/50, 33/33, 25/25... | `max(semanas_proyecto) + 1`, en cascada temporal |

**Lo que aclara v0.5:** v0.4 no describía explícitamente que las fracciones son las mismas en ambos modos. La ausencia de esta aclaración generaba la confusión de que el modo Secuencial podía tener un reparto diferente. v0.5 cierra esa ambigüedad.

**Regla de cascada temporal (secuencial):**
```
Destino 1: empieza en max(semanas_proyecto) + 1
Destino 2: empieza donde terminó el Destino 1
Destino 3: empieza donde terminó el Destino 2
```

---

### A.3 — Aclaración de textos de UI (commit `4372f181`)

**Qué cambia en v0.5:**
Se corrigen tres textos de interfaz que describían incorrectamente el comportamiento de los modos Paralelo y Secuencial.

#### A.3.1 Radio Paralelo/Secuencial — texto de ayuda

**Texto anterior (v0.4):**
> "Paralelo: mueve el exceso a otra línea en las mismas semanas donde aparece el déficit. Secuencial: mantiene el comportamiento actual y coloca el residual en semanas posteriores."

**Problemas del texto anterior:**
- "mantiene el comportamiento actual" no describe una regla, sino el estado del código en un momento dado. Después del hotfix `0e1db08f`, el texto ya no era ni correcto ni descriptivo.
- No mencionaba que las fracciones son iguales en ambos modos.

**Texto vigente (v0.5):**
> "Paralelo: el exceso se reparte entre las líneas destino y se coloca en las mismas semanas del conflicto. Secuencial: el exceso se reparte igual, pero se coloca después del tramo principal del proyecto, en cascada temporal entre destinos. La diferencia es temporal, no de porcentaje."

#### A.3.2 Orientación para lote divisible — texto informativo

**Texto anterior (v0.4):**
> "…Elige Paralelo si el exceso puede repartirse entre unidades/líneas, o Secuencial si debe ejecutarse después."

**Texto vigente (v0.5):**
> "…Paralelo: el exceso se reparte entre destinos en las mismas semanas del conflicto. Secuencial: el exceso se reparte igual, pero se coloca después del tramo principal del proyecto, en cascada temporal entre destinos."

#### A.3.3 Banner de simulación activa

**Texto anterior (v0.4):**
> "⚠ Simulación activa — el plan real no ha cambiado."

**Texto vigente (v0.5):**
> "⚠ Simulación activa — el plan real no ha cambiado. Para descartar todos los cambios, usa el botón 'Reiniciar simulación'."

**Lo que añade v0.5:** la referencia explícita al botón de reinicio, que antes no se mencionaba en el banner.

---

### A.4 — Semana bloqueada: usar capacidad libre antes de detener (C3, confirmado en v0.5)

**Qué dice v0.5:**
Esta regla procede de Anexo v0.3 (A.3). En la versión inicial del documento v0.5 se documentó incorrectamente como "Bloqueada — cálculo se detiene" sin mencionar el uso de la capacidad libre. v0.5 corrige esa omisión documental.

**Regla correcta:**
Cuando la colocación encuentra desde la segunda semana del movimiento una semana con carga de otro proyecto/modelo:

1. Calcular `capacidad_libre = capacidad_nominal − carga_otro_proyecto`.
2. Colocar `min(pendiente, capacidad_libre)` en esa semana.
3. Detener la colocación.
4. Registrar carga no absorbida con causa "línea ocupada por otro proyecto".

No se salta esa semana para buscar huecos posteriores.

**Diferencia con la documentación inicial de v0.5:** el documento original de v0.5 (primera versión) decía "Bloqueada — cálculo se detiene", que era correcto en cuanto al comportamiento final (se detiene), pero omitía que antes de detenerse se usa la capacidad libre disponible en esa semana.

**Estado de implementación:** implementado en commit `fcd86588` — Fix blocked-week partial residual placement. Este commit pertenece a la cadena previa a v0.5 y no es nuevo en v0.5, pero la documentación de v0.5 lo omitió en su primera versión.

---

### A.5 — Corrección de la fórmula de exceso (documental)

**Problema detectado:**
La fórmula documentada en la primera versión de v0.5 era:

```
exceso_semana_W = max(0, carga_proyecto_en_W − capacidad_disponible_en_W)
```

Esta fórmula es incorrecta porque no acota el exceso a la carga real del proyecto. Si la capacidad disponible es negativa (varios proyectos sobrecargan la línea), el exceso calculado puede superar la carga real del proyecto.

**Fórmula correcta (vigente en v0.5):**

```
exceso_semana_W = min(
    carga_proyecto_en_W,
    max(0, carga_total_linea_en_W − capacidad_nominal_linea_en_W)
)
```

**Dos acotaciones fundamentales:**
- No se mueve más carga que la del propio proyecto en esa semana.
- No hay exceso si la línea no está en déficit real (carga total ≤ capacidad nominal).

---

## B. Reglas que NO cambian respecto a v0.4

Las siguientes reglas de v0.4 se mantienen íntegramente:

- Plan real = Excel original, no se modifica nunca.
- Simulación activa = copia de trabajo acumulativa.
- No se pierden ni se duplican horas.
- No se descuenta del origen más de lo colocado en destino.
- Primera ronda: mover completo o ampliar semanas.
- Mover exceso no es acción normal de primera ronda.
- Fracciones proporcionales iguales entre destinos.
- Cascada temporal en modo secuencial: D2 empieza donde terminó D1.
- Exclusividad de línea: carga de otro proyecto bloquea.
- Carga del mismo proyecto en destino no bloquea por exclusividad.
- Semana de transición requiere confirmación explícita del usuario.
- No se buscan huecos discontinuos.
- Carga no absorbida siempre se registra con la causa.
- Segunda ronda combina acciones sobre proyectos distintos.
- engine.py no se toca salvo necesidad demostrada y aprobada.

---

## C. Trazabilidad de implementación

| Regla | Estado | Commit |
|---|---|---|
| A.1 — `max(semanas)+1` para todos los tipos (secuencial) | **Implementado** | `0e1db08f` |
| A.2 — Distinción temporal no de porcentaje (aclaración) | **Documentado y en UI** | `4372f181` |
| A.3.1 — Texto radio Paralelo/Secuencial | **Implementado** | `4372f181` |
| A.3.2 — Texto orientación lote divisible | **Implementado** | `4372f181` |
| A.3.3 — Banner simulación activa con botón reinicio | **Implementado** | `4372f181` |

---

## D. Análisis de la regresión corregida

### D.1 Línea de tiempo del bug

| Commit | Acción | Efecto |
|---|---|---|
| `78b9280a` | Base validada: `max+1` para todos los tipos | Correcto |
| `95de844f` | Introduce rama por tipo: `max+1` solo para equipo_unico; `min(afectadas)` para el resto | **REGRESIÓN** |
| `ba7867f0` | Añade exclusividad de línea y modo paralelo separado | No toca `_sem_cursor` |
| `0e1db08f` | Corrección: `max+1` para todos | **Regresión corregida** |

### D.2 Impacto de la regresión

La regresión de `95de844f` hacía que para proyectos de tipo lote_divisible, fase_transferible y desconocido en modo Secuencial:

- `_sem_cursor` se inicializaba en `min(_semanas_afectadas)` (primera semana con exceso vivo).
- `min(_semanas_afectadas)` es exactamente la semana de inicio que usa el modo Paralelo.
- El resultado visual: secuencial y paralelo producían resultados idénticos para esos tipos.
- El planificador no podía distinguir el efecto de elegir un modo u otro.

### D.3 Solución mínima aplicada

```python
# Antes (regresión):
if tipo_proyecto == "equipo_unico":
    _sem_cursor = max(_semanas) + 1
else:
    _sem_cursor = min(_semanas_afectadas)

# Después (corrección):
_sem_cursor = max(_semanas) + 1
```

El cambio mínimo elimina la rama condicional y aplica la regla uniforme a todos los tipos. La cascada temporal (`_sem_cursor = _sem_act` al final de cada destino) permanece intacta: es correcta y no era parte de la regresión.

---

*Fin del Anexo v0.5.*
