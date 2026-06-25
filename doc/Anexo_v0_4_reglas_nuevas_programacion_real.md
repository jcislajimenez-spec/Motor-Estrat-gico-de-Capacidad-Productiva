# Anexo v0.4 — Lógica operativa de "Mover proyecto completo"
## Programación real · Reglas operativas de simulación

---

**Fecha:** 2026-06-22  
**Versión base:** v0.3  
**Versión resultante:** v0.4  
**Carácter:** Explicación de por qué falló la implementación anterior, por qué las reglas son como son, y checklist de validación antes de volver al código.

---

## A. Por qué falló la implementación anterior

### A.1 El commit revertido: 951e95d1

El commit `951e95d1 Add full project move recalculation` introdujo la función `_simulate_prog_move_full` que debía implementar "Mover proyecto completo" con recálculo de duración en destino. Fue revertido mediante `615975ac Revert "Add full project move recalculation"` porque falló la validación funcional.

### A.2 Los tres errores fundamentales

**Error 1 — M3 dejaba carga residual en origen:**

La función implementaba dos ramas en M3:

```python
if _colocado_h >= _carga_total_h - 0.001:
    # Movimiento completo: eliminar filas de origen  ← CORRECTO
    ...
else:
    # Movimiento parcial: reducir origen por lo colocado  ← INCORRECTO
    _reduccion_restante_m3 = _colocado_h
    ...
```

Cuando el destino no absorbía toda la carga (`_colocado_h < _carga_total_h`), la rama "movimiento parcial" reducía el origen solo en las horas que cabían en destino. Las horas restantes permanecían en origen. Esto es exactamente lo contrario de "mover completo": el origen no quedaba vacío.

**Error 2 — El checkbox confirmaba "movimiento parcial":**

El texto del checkbox era:
```
"Confirmo la semana de transición y acepto el movimiento parcial"
```
Una acción llamada "mover completo" ofrecía un checkbox que confirmaba explícitamente un "movimiento parcial". El usuario no podía saber qué estaba autorizando realmente.

**Error 3 — La UI mezclaba mover + ampliar simultáneamente:**

El bloque de código contenía:
```python
# ── Bloqueo: ampliar + mover completo recalculado ──
if _comb_ok and _ml_has_sel and _as_has_sel:
```
La condición evaluaba que el usuario tuviera seleccionada a la vez una acción de mover línea Y una acción de ampliar semanas. La regla dice explícitamente que estas dos acciones no pueden combinarse en una sola. Este bloque lo permitía.

### A.3 La causa raíz

Los tres errores tienen una causa raíz común: la implementación confundió dos conceptos distintos en un mismo flujo:

| Concepto | Primera ronda | Segunda ronda |
|---|---|---|
| Mover completo | Mueve TODO el proyecto; origen vacío; déficit vivo en destino | No es acción normal (F6 de v0.3) |
| Ampliar semanas | Acción independiente en la misma línea | Acción para tratar déficit residual |
| Reprogramar residual | No disponible | Acción para mover el EXCESO |

Al mezclarlos, la función producía estados incoherentes: parte del proyecto en origen, parte en destino, con horas que no sumaban bien, y un Gantt que mostraba una situación imposible industrialmente.

---

## B. Por qué mover completo no puede dejar carga en origen

### B.1 La regla industrial

Un proyecto en producción ocupa física y logísticamente una línea. "Mover el proyecto completo" a otra línea significa que desde la semana de aplicación, el proyecto ya no está en la línea origen. No puede estar en dos sitios a la vez.

Dejar carga en origen después de "mover completo" crea una situación industrialmente imposible:
- La línea origen reporta trabajo del proyecto → los operarios de esa línea reciben órdenes para un proyecto que ya no está ahí.
- La línea destino también reporta trabajo del proyecto → los operarios de destino reciben el mismo proyecto.
- El Gantt muestra el proyecto en dos líneas → el responsable de producción no sabe dónde está el proyecto realmente.

### B.2 La regla de conservación no justifica dejar carga en origen

La regla B3 de v0.3 dice "no se pierden horas". Esto no significa que las horas deban quedarse en origen si no caben en destino. Significa que la suma total de horas del proyecto debe ser la misma antes y después de cualquier acción.

**Con Opción A (regla de v0.4):** todas las horas del proyecto pasan a destino. Suma conservada. Si en destino hay semanas donde la suma de cargas supera la capacidad, esas semanas tienen déficit. El déficit es el problema a resolver en segunda ronda, no un motivo para dejar horas en origen.

```
Antes: horas_origen = H       horas_destino_proyecto = 0
Después: horas_origen = 0     horas_destino_proyecto = H
Conservación: H = H ✓
Déficit en destino si: H_semana_destino > capacidad_destino_semana → se muestra como déficit vivo
```

---

## C. Por qué no se puede mover y ampliar en la misma acción

### C.1 La regla

"Mover completo" y "Ampliar semanas" son acciones de distinta naturaleza:

| "Mover completo" | "Ampliar semanas" |
|---|---|
| Cambia la línea del proyecto | No cambia la línea |
| Puede acortar si cabe en menos semanas; nunca alarga automáticamente | Extiende la duración temporalmente |
| Elimina todo de origen | No hay origen que vaciar |
| El déficit queda en destino (si no cabe) | El déficit puede resolverse con las semanas extra |

Aplicarlas simultáneamente produce un resultado imposible de interpretar:

> ¿El proyecto está en la línea nueva (mover) o en la misma con más tiempo (ampliar)? ¿Las semanas extra son en la línea nueva o en la original? ¿El déficit que queda es de mover o de ampliar?

### C.2 El error concreto del commit revertido

El bloque `if _comb_ok and _ml_has_sel and _as_has_sel` intentaba manejar el caso en que el usuario había seleccionado ambas acciones. En lugar de bloquearlo, el código intentaba orquestar ambas secuencialmente. El resultado: el proyecto podía quedar distribuido entre tres estados (parte en origen reducido, parte en destino recalculado, parte en semanas extendidas).

### C.3 La regla para v0.4

Si el usuario selecciona "Mover línea" y "Ampliar semanas" para el mismo proyecto en el mismo paso de primera ronda, la UI debe mostrar un error bloqueante claro:

```
"No se puede mover el proyecto completo y ampliar semanas simultáneamente.
Aplica primero el movimiento. Si el destino genera déficit, usa segunda ronda para ampliar."
```

---

## D. Por qué el déficit queda en destino

### D.1 La regla

Cuando el proyecto se mueve completo a destino y la capacidad de destino no absorbe toda la carga en el tramo original del proyecto, el déficit queda en destino porque:

1. **El proyecto está en destino.** No en origen. Industrialmente, los operarios de destino son los responsables del proyecto desde el momento del movimiento.
2. **El problema es de capacidad en destino.** La línea destino no tiene suficiente capacidad para el proyecto tal como está dimensionado en el tramo temporal. Eso es un problema de la línea destino, no un motivo para devolver el proyecto a origen.
3. **La segunda ronda tiene las herramientas para resolverlo.** El responsable de producción puede: ampliar semanas del proyecto en destino, reprogramar parte del residual a otra línea, o decidir no actuar y aceptar el déficit.

### D.2 El déficit es una señal, no un error de la app

La app no ha fallado si después de "mover completo" hay déficit en destino. La app ha hecho su trabajo: ha movido el proyecto, ha conservado las horas, y ha mostrado el problema real. El problema ya existía antes (la línea destino tiene menos capacidad); ahora es visible donde corresponde.

---

## E. Por qué se elige Opción A frente a Opción B

### E.1 Definición de las opciones

> **Contexto:** Opción A y Opción B solo aplican cuando el proyecto no cabe dentro del tramo original en destino. Cuando el destino tiene más capacidad y el proyecto sí cabe en menos semanas, el movimiento produce el acortamiento y no hay déficit que representar. Las opciones A y B son irrelevantes en ese caso.

**Opción A (caso en que no cabe):** Las filas del proyecto se trasladan a la línea destino manteniendo el mismo patrón semanal (mismas semanas, mismas horas por semana). Si la capacidad de destino es insuficiente en alguna semana, esa semana muestra déficit vivo de forma orgánica.

**Opción B (caso en que no cabe):** Se aplica un cálculo laminar semana a semana: se coloca en cada semana lo que cabe (hasta capacidad nominal), y las horas que no caben se acumulan en la última semana del tramo como un pico de déficit.

### E.2 Por qué Opción A es mejor para v0.4

| Criterio | Opción A | Opción B |
|---|---|---|
| **Fidelidad industrial** | El proyecto mantiene su ritmo semanal real | El pico al final no representa cómo trabaja una línea |
| **Legibilidad del Gantt** | El déficit se ve en las semanas donde ocurre | El pico artificial puede confundirse con un error de datos |
| **Decisiones en segunda ronda** | El planner ve exactamente qué semanas tienen problema | El pico no mapea directamente a semanas individuales |
| **Conservación de horas** | Trivial: mismas horas, distinta línea | Requiere gestionar el pico como fila especial o "horas flotantes" |
| **Complejidad de implementación** | 5–10 líneas: relabel de filas | >100 líneas: loop con horizonte, gestión de pico, validación especial |
| **Riesgo de regresión** | Mínimo: lógica similar a `_simulate_prog_move_line` existente | Alto: nueva lógica compleja, el commit revertido ya mostró este riesgo |
| **Compatibilidad con déficit existente** | El cálculo de déficit de la app funciona sin cambios | Requiere lógica especial para el pico |

### E.3 Cuándo tiene sentido Opción B (v0.5)

Opción B es industrialmente interesante cuando la app ofrezca explícitamente "Mover y optimizar duración": el responsable de producción quiere ver cómo quedaría el proyecto con el ritmo optimizado a la capacidad del destino, no con el ritmo del origen. Eso es una acción distinta y puede ser una mejora de v0.5.

---

## F. Ejemplos operativos

### F.1 Caso nominal — Destino con misma capacidad

**Situación:** PRY-005 está en N1-L10 de S8 a S12, 100 h/sem. Destino N1-L11 tiene 100 h/sem disponibles.

| Semana | En N1-L10 antes | En N1-L11 antes | En N1-L10 después | En N1-L11 después |
|---|---|---|---|---|
| S8 | 100 h | 0 h | **0 h** | **100 h** |
| S9 | 100 h | 0 h | **0 h** | **100 h** |
| S10 | 100 h | 0 h | **0 h** | **100 h** |
| S11 | 100 h | 0 h | **0 h** | **100 h** |
| S12 | 100 h | 0 h | **0 h** | **100 h** |

Resultado: origen vacío, destino con proyecto completo, sin déficit. ✓

### F.2 Caso crítico — Destino con menos capacidad

**Situación:** PRY-005 está en N1-L10 de S8 a S12, 100 h/sem. Destino N1-L11 tiene 60 h/sem disponibles.

| Semana | En N1-L10 antes | En N1-L11 antes | En N1-L10 después | En N1-L11 después | Déficit N1-L11 |
|---|---|---|---|---|---|
| S8 | 100 h | 0 h | **0 h** | **100 h** | 40 h ← déficit vivo |
| S9 | 100 h | 0 h | **0 h** | **100 h** | 40 h ← déficit vivo |
| S10 | 100 h | 0 h | **0 h** | **100 h** | 40 h ← déficit vivo |
| S11 | 100 h | 0 h | **0 h** | **100 h** | 40 h ← déficit vivo |
| S12 | 100 h | 0 h | **0 h** | **100 h** | 40 h ← déficit vivo |

Resultado: origen vacío (MV-01 ✓), déficit vivo en destino (MV-03 ✓), horas conservadas (MV-11 ✓). La segunda ronda puede ampliar semanas o reprogramar residual.

**Lo que habría ocurrido con el commit revertido (INCORRECTO):**

| Semana | En N1-L10 después (MAL) | En N1-L11 después (MAL) |
|---|---|---|
| S8 | 40 h (residual mal) | 60 h |
| S9 | 40 h (residual mal) | 60 h |
| S10 | 40 h (residual mal) | 60 h |
| S11 | 40 h (residual mal) | 60 h |
| S12 | 40 h (residual mal) | 60 h |

El proyecto aparecía en DOS líneas simultáneamente. Industrialmente imposible para equipo único.

### F.3 Caso de acortamiento — Destino con más capacidad

**Situación:** PRY-005 está en N1-L10 de S8 a S12, 100 h/sem (500 h totales). Destino N1-L11 tiene 167 h/sem disponibles reales (capacidad nominal = 167 h/sem, sin carga preexistente en este ejemplo). El proyecto cabe en ⌈500/167⌉ = 3 semanas dentro del tramo S8–S12.

Vista previa muestra: "Con la capacidad de N1-L11 (167 h/sem), el proyecto se completa en 3 semanas (S8–S10). Origen quedará vacío."

Si el usuario aplica:

| Semana | En N1-L10 después | En N1-L11 después | Notas |
|---|---|---|---|
| S8 | 0 h | **167 h** | Primera semana acortada |
| S9 | 0 h | **167 h** | Segunda semana acortada |
| S10 | 0 h | **166 h** | Tercera semana (ajuste de redondeo) |
| S11 | 0 h | 0 h | Semana libre — sin carga del proyecto |
| S12 | 0 h | 0 h | Semana libre — sin carga del proyecto |

Resultado: origen vacío (MV-01 ✓), proyecto completo en destino en 3 semanas (MV-06 ✓), sin ampliación automática (MV-05 ✓), horas conservadas: 167+167+166 = 500 h (MV-11 ✓). Sin déficit.

> **Nota:** En este caso el acortamiento es el resultado real del movimiento, no un advisory. Opción A (mismo patrón semanal) solo aplica cuando no cabe en menos semanas. Aquí cabe, luego el movimiento produce el acortamiento.

### F.4 Caso de transición — Primer semana del destino con otro proyecto

**Situación:** PRY-005 a mover a N1-L11 empezando en S8. En S8 de N1-L11 ya existe PRY-009 con 40 h.

La app detecta: "Hay carga de otro proyecto (PRY-009) en la primera semana del movimiento (S8 de N1-L11)."

Aparece aviso y checkbox:
```
"Confirmo que hay carga de PRY-009 en S8 de N1-L11 y aplico el movimiento completo."
```

Si el usuario confirma: el movimiento aplica. En S8 de N1-L11 quedan: 100 h (PRY-005) + 40 h (PRY-009) = 140 h. Si cap. N1-L11 = 100 h → déficit de 40 h en S8 → conflicto visible. Origen PRY-005 queda vacío.

Si el usuario NO confirma: el botón Aplicar permanece bloqueado.

---

## G. Casos de prueba PT-13 a PT-24

Estos casos son obligatorios para validar la implementación de v0.4 en código. Se añaden a los PT-01 a PT-12 de v0.3.

| # | Caso | Condición de aceptación |
|---|---|---|
| PT-13 | Mover completo → destino misma capacidad | `sum(h_origen_tras) == 0` y `sum(h_destino_tras) == sum(h_origen_antes)` y ninguna semana en déficit |
| PT-14 | Mover completo → destino menos capacidad | `sum(h_origen_tras) == 0` y déficit vivo en destino visible en tabla y Gantt; ninguna hora en origen |
| PT-15 | Mover completo → destino más capacidad | Destino con más capacidad → al aplicar Mover completo, el proyecto queda en destino en menos semanas dentro del tramo original; `sum(h_origen_tras) == 0`; `sum(h_destino_tras) == sum(h_origen_antes)`; ninguna fila del proyecto en semanas más allá del tramo acortado; sin ampliación automática |
| PT-16 | No amplía semanas automáticamente | Ninguna fila del proyecto en destino tiene Semana > semana_fin_actual_original tras mover completo |
| PT-17 | Segunda ronda disponible tras déficit vivo | Después de PT-14, las opciones de segunda ronda aparecen para el proyecto en destino |
| PT-18 | Transición: checkbox obligatorio | Cuando S_inicio_destino tiene otro proyecto, aparece checkbox; botón Aplicar bloqueado sin confirmar |
| PT-19 | Sin checkbox: no aplica | Con checkbox requerido y sin marcar: acción no se ejecuta; estado anterior conservado |
| PT-20 | Conflicto de otro proyecto en destino → visible en destino | `sum(h_origen_tras_proyecto) == 0`; conflicto (carga_total_destino_semana > cap_destino) visible en la línea destino |
| PT-21 | Texto del checkbox | Buscar en la UI el texto del checkbox: no contiene "movimiento parcial", no contiene "parcial" en ninguna variante |
| PT-22 | Origen = 0 en todos los escenarios | Para todos los PT anteriores: `df_sim[df_sim['Proyecto']==P][df_sim['Línea']==L_origen]['Horas proyecto semana'].sum() == 0` |
| PT-23 | Gantt muestra problema en destino | Tras PT-14 o PT-20: en Gantt, la línea origen no muestra barras del proyecto; la línea destino muestra barras y las semanas con déficit aparecen marcadas |
| PT-24 | v0.3 intacta | Los cuatro archivos v0.3 tienen fechas de modificación anteriores a v0.4; su contenido es idéntico al original |
| PT-25 | Seleccionar "Mover proyecto completo" + "Ampliar semanas" para el mismo proyecto en la misma ronda | Error bloqueante; no se aplica ninguna acción; la simulación no se modifica; mensaje claro: "No se puede mover y ampliar el mismo proyecto en una sola acción. Aplica una acción y revisa la segunda ronda." |
| PT-26 | Mover completo a destino con menos capacidad — verificar ausencia de pico artificial Opción B | `sum(h_origen_tras) == 0`; déficit vivo en destino semana a semana; no hay acumulación artificial en la última semana; no aparece pico final tipo Opción B; Gantt muestra déficit en las semanas reales donde ocurre |
| PT-27 | Destino con más capacidad nominal pero con carga preexistente en algunas semanas | El acortamiento solo se calcula con capacidad disponible real (nominal − carga preexistente). Si el proyecto no cabe con esa capacidad real, se muestra déficit vivo en destino semana a semana. No se usa solo la capacidad nominal para decidir el acortamiento. |

---

## H. Checklist de validación antes de tocar código

Estos puntos deben estar aprobados explícitamente antes de escribir ninguna línea de implementación:

| ID | Validación | Estado |
|---|---|---|
| BL-01 | **Opción A aprobada** como regla base para representar déficit en destino | ✅ Aprobada en v0.4 |
| BL-02 | **F7 matizado en mover completo**: puede acortar dentro del tramo original; no autoriza alargar automáticamente | ✅ Aprobado en v0.4 |
| BL-03 | **Horizonte = tramo original** (semana_inicio a semana_fin_actual) | ✅ Cerrado en v0.4 MV-04 |
| BL-04 | **Texto correcto del checkbox** sin "movimiento parcial" | ✅ Cerrado en v0.4 Sección 4.3–4.4 |
| BL-05 | **UI bloquea mover + ampliar** simultáneos para el mismo proyecto | ✅ Aprobado en v0.4 MV-07 |
| BL-06 | **PT-13 a PT-27** son los casos de prueba correctos y suficientes | Pendiente validación con usuario |
| BL-07 | **F6 de v0.3 se mantiene**: mover completo no es acción normal en segunda ronda | ✅ Confirmado en v0.4 Sección 5.1 tabla 2ª ronda |

### Pseudocódigo de referencia para implementación (Opción A)

El siguiente pseudocódigo describe la lógica de "mover completo" con Opción A. NO es código de producción; es una referencia funcional para que el implementador no repita los errores del commit revertido.

```python
def simular_mover_completo_v0_4(load_df, proyecto, linea_origen, linea_destino,
                                 cap_nominal_h, carga_preexistente_por_semana=None):
    """
    Mover completo v0.4:
    - Si destino tiene más capacidad disponible real y cabe en menos semanas: acorta (MV-06).
    - Si no cabe en menos semanas: mismo patrón en destino, déficit orgánico (Opción A).
    - Origen siempre vacío (MV-01, MV-02).
    - Sin ampliación automática de semanas (MV-05).

    IMPORTANTE — capacidad disponible real (MV-06, PT-27):
    cap_disponible_sem = cap_nominal_h − carga ya existente en destino en esa semana
    (carga de otros proyectos/modelos ya colocados en linea_destino dentro del tramo original)
    El acortamiento solo se aplica si el proyecto completo cabe dentro del tramo original
    usando cap_disponible_sem; NUNCA se decide el acortamiento con solo cap_nominal_h
    ignorando la carga preexistente.
    """
    sim = load_df.copy()
    if carga_preexistente_por_semana is None:
        carga_preexistente_por_semana = {}

    # Identificar filas del proyecto en origen
    mask_origen = (
        (sim["Proyecto"] == proyecto) &
        (sim["Línea"] == linea_origen)
    )
    if not mask_origen.any():
        return {"error": "El proyecto no tiene filas en la línea origen"}

    filas_origen = sim.loc[mask_origen].copy()
    h_antes = round(float(filas_origen["Horas proyecto semana"].sum()), 4)
    semanas_orig = sorted(filas_origen["Semana"].astype(int).unique().tolist())
    semana_inicio = min(semanas_orig)
    semana_fin_actual = max(semanas_orig)
    n_semanas_orig = len(semanas_orig)

    # M3: eliminación INCONDICIONAL de origen (sin ramas de movimiento parcial)
    sim = sim.loc[~mask_origen].copy()

    # Capacidad disponible real por semana = nominal − carga preexistente de otros proyectos
    cap_disp = {
        sem: max(0.0, float(cap_nominal_h) - float(carga_preexistente_por_semana.get(sem, 0.0)))
        for sem in semanas_orig
    }

    # ¿Cabe el proyecto en menos semanas usando la capacidad disponible real?
    pendiente_test = h_antes
    semanas_usadas = 0
    for sem in semanas_orig:
        if pendiente_test <= 0:
            break
        pendiente_test = round(pendiente_test - cap_disp[sem], 4)
        semanas_usadas += 1
    # puede_acortar solo si cabe completo dentro del tramo y en menos semanas que las originales
    puede_acortar = (pendiente_test <= 0 and semanas_usadas < n_semanas_orig)

    if puede_acortar:
        # Acortamiento: colocar laminado usando capacidad disponible real
        filas_nuevas = []
        pendiente = h_antes
        fila_tmpl = filas_origen.iloc[0].to_dict()
        for sem in semanas_orig:
            if pendiente <= 0:
                break
            if sem > semana_fin_actual:
                break  # No ampliar semanas (MV-05)
            h_sem = round(min(pendiente, cap_disp[sem]), 4)
            if h_sem > 0:
                nueva = dict(fila_tmpl)
                nueva["Línea"] = linea_destino
                nueva["Semana"] = sem
                nueva["Horas proyecto semana"] = h_sem
                filas_nuevas.append(nueva)
            pendiente = round(pendiente - h_sem, 4)
        sim = pd.concat([sim, pd.DataFrame(filas_nuevas)], ignore_index=True)
        acortado = True
    else:
        # Opción A: mismo patrón semanal en destino; déficit orgánico si hay
        filas_dest = filas_origen.copy()
        filas_dest["Línea"] = linea_destino
        sim = pd.concat([sim, filas_dest], ignore_index=True)
        acortado = False

    # Verificar conservación de horas (MV-11)
    h_despues = round(float(
        sim.loc[(sim["Proyecto"] == proyecto) & (sim["Línea"] == linea_destino),
                "Horas proyecto semana"].sum()
    ), 4)
    assert abs(h_antes - h_despues) < 0.1, f"Conservación fallida: {h_antes} != {h_despues}"

    # El déficit en destino (si hay) lo calcula el motor de capacidad existente
    return {"load_df": sim, "moved_ok": True, "acortado": acortado}
```

Este pseudocódigo muestra las dos ramas de v0.4:
- `puede_acortar = True`: acortamiento laminar usando `cap_disp` (real) → el resultado incluye realmente menos semanas.
- `puede_acortar = False`: Opción A (relabel) → el déficit lo detecta el motor de capacidad existente.

Ambas ramas cumplen MV-01 (origen vacío), MV-05 (sin ampliar) y MV-11 (conservación).

**Diferencia clave respecto a v0.3 / commit revertido:** `cap_disp[sem]` es la capacidad disponible real por semana, no la capacidad nominal bruta. Si hay carga preexistente en algunas semanas, esas semanas tienen menos capacidad real. El acortamiento solo se declara posible si el proyecto cabe completo dentro del tramo original con esa capacidad real.

---

## I. Qué NO cambia respecto a v0.3

Las siguientes reglas de v0.3 se mantienen íntegramente y no deben reinterpretarse:

- Plan real = Excel original, no se modifica nunca.
- Simulación activa = copia de trabajo.
- No se pierden ni se duplican horas.
- Primera ronda: mover completo primero si encaja mejor.
- Ampliar semanas: segunda opción fuerte cuando no hay destino viable.
- Residual no es acción normal de primera ronda.
- Primera semana con otro proyecto = semana de transición (requiere confirmación explícita).
- "No actuar" siempre disponible con diagnóstico.
- Columnas "En sim." y "Bloqueo" funcionando.
- engine.py no se toca salvo necesidad demostrada.
- C2 y C3 (no buscar huecos discontinuos) aplican a reprogramar residual.
- C4 (equipo único: residual secuencial posterior) sin cambio.
- F1–F9 (reglas físicas) sin cambio.
- B1–B8 (bloqueantes) sin cambio.

---

*Fin del Anexo v0.4.*
