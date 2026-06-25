# DOCUMENTO BASE — Manual de Usuario
## Módulo Programación real
### Motor Estratégico de Capacidad Productiva · INGETEAM
### Versión de referencia: junio 2026 (v0.5)

---

> **Propósito de este documento:** manual de referencia independiente para el módulo Programación real del Motor Estratégico. Refleja el estado funcional en staging/producción tras los commits de referencia: `78b9280a`, `036cb323`, `0d286768`, `0e1db08f`, `4372f181` (junio 2026). Cubre desde la carga del Excel hasta la segunda ronda, incluyendo modos Paralelo y Secuencial, regla de exclusividad de línea y clasificación funcional de alternativas.

---

## 1. QUÉ ES PROGRAMACIÓN REAL

El módulo **Programación real** (Tab 6) responde a una pregunta concreta:

> *¿El plan de proyectos que tenemos comprometido cabe en la capacidad de la planta, semana a semana y línea a línea?*

No es un ERP ni un secuenciador automático. Es una **capa de decisión** que pone en contacto la lista real de proyectos (cargada desde Excel) con la capacidad calculada del escenario activo.

### 1.1 Qué responde el módulo

- ¿El plan cabe?
- ¿Dónde se rompe? ¿En qué semana? ¿En qué línea?
- ¿Cuántas horas faltan?
- ¿Qué proyectos están implicados en el conflicto?
- ¿Hay alguna alternativa candidata de línea?
- ¿Qué pasaría si se mueve ese proyecto a otra línea?
- ¿Qué queda pendiente después de aplicar una acción?

### 1.2 Qué NO hace el módulo

- No optimiza la secuencia de proyectos.
- No calcula el estado real de materiales.
- No aplica cambios automáticamente.
- No modifica el Excel original.

### 1.3 Perfil de usuario

| Perfil | Uso principal |
|---|---|
| Planificador / Responsable de producción | Carga Excel, calcula, detecta conflictos, aplica acciones simuladas, revisa segunda ronda. |
| Ingeniero de procesos | Puede revisar auditoría técnica y alternativas candidatas. |
| Dirección | Puede leer veredicto, KPIs y Gantt. |

---

## 2. CONDICIONES PREVIAS

Antes de usar el módulo deben estar cubiertas cuatro condiciones:

1. **Escenario activo configurado en Planificación:** con modelos asignados a las líneas que se quieren analizar.
2. **Líneas con modelo asignado:** solo las líneas con modelo generan capacidad calculable.
3. **Parámetros de planta cargados:** turnos, disponibilidad, eficiencia y tiempos de proceso deben estar en la base de datos.
4. **Excel con hoja PROGRAMACION_REAL:** la hoja debe existir con las columnas obligatorias.

Si alguna condición no se cumple, la app muestra un aviso específico.

---

## 3. ESTRUCTURA DEL EXCEL

El Excel debe contener una hoja llamada exactamente `PROGRAMACION_REAL` (sin acento, en mayúsculas). Una fila = un proyecto.

### 3.1 Columnas obligatorias

| Columna | Tipo | Descripción |
|---|---|---|
| `Proyecto` | Texto | Nombre o código del proyecto. Único por fila. |
| `Modelo / familia` | Texto | Familia de producto o modelo (ej: PT0163, SL, GW). |
| `Cantidad` | Numérico | Número de unidades del proyecto. |
| `Semana inicio mínima` | Entero 1–52 | Primera semana en que el proyecto puede empezar. |
| `Semana entrega objetivo` | Entero 1–52 | Semana límite de entrega. |
| `Horas totales` | Numérico ≥ 1 | Total de horas de trabajo del proyecto. |
| `Prioridad` | Numérico | Orden de prioridad (menor = más prioritario). |

### 3.2 Columnas opcionales clave

| Columna | Valor por defecto | Descripción |
|---|---|---|
| `Duración semanas` | Calculada | Si vacía: `Semana entrega − Semana inicio + 1`. |
| `Línea preferente` | Vacío | Línea donde se ejecuta el proyecto. |
| `Líneas alternativas` | Vacío | Líneas candidatas separadas por coma. |
| `Tipo de proyecto` | Vacío | `equipo_unico`, `lote_divisible`, `fase_transferible` o `desconocido`. Afecta a los avisos de segunda ronda. |
| `Nº unidades` | 1 | Número de unidades del proyecto. |

### 3.3 Aliases industriales aceptados

Si el Excel usa nombres de columna distintos, el sistema los detecta y renombra:

| Si el Excel trae... | Se interpreta como |
|---|---|
| `Codigo`, `CODIGO`, `Código` | `Proyecto` |
| `GAMA` | `Modelo / familia` |
| `TOTAL` | `Horas totales` |
| `EQUIPO` | `Equipo / modelo` |

---

## 4. CÓMO USAR EL MÓDULO — PASO A PASO

### Paso 1 — Cargar el Excel

En la franja superior de la pantalla, arrastra o selecciona el archivo `.xlsx`. El sistema detecta automáticamente si el archivo cambió (por hash) e invalida el resultado anterior si es necesario.

El estado de validación indica:
- `✓ N proyectos` — validado correctamente.
- `⚠ N avisos` — avisos no bloqueantes (columnas opcionales ausentes, etc.).
- `✗ Error` — hay un problema que impide el cálculo.

### Paso 2 — Verificar el escenario activo

En la misma franja, el bloque de contexto muestra: escenario activo, nombre de planta, número de líneas planificadas y capacidad total. Verifica que es el escenario correcto antes de calcular.

### Paso 3 — Calcular programación real

Pulsa el botón **"Calcular programación real"**. Este botón solo aparece cuando hay un Excel válido y hay capacidad calculada.

El cálculo:
1. Resuelve la línea de cada proyecto (preferente → alternativas → excluido si no hay línea).
2. Calcula la duración activa de cada proyecto.
3. Reparte las horas totales de forma uniforme entre las semanas activas del proyecto.
4. Agrega la carga por semana y línea.
5. Detecta dónde la carga supera la capacidad.

### Paso 4 — Leer el veredicto

Tras el cálculo, aparece un mensaje ejecutivo:

- 🔴 **Con conflictos:** "Se detectan conflictos de capacidad. Primera semana crítica: N. Línea más tensionada: X. Déficit acumulado: Y h."
- 🟡 **Sin conflictos pero con excluidos:** aviso con número de proyectos fuera del cálculo.
- 🟢 **El plan cabe:** todos los proyectos calculados tienen capacidad suficiente.

Bajo el veredicto, cinco KPIs compactos:

| KPI | Descripción |
|---|---|
| Excluidos | Proyectos sin línea resuelta |
| Semanas conflicto | Número de semanas con déficit |
| Primera crítica | Primera semana en que hay déficit |
| Déficit total h | Suma del déficit en horas |
| Línea más tensionada | Línea con mayor déficit acumulado |

### Paso 5 — Revisar el Gantt y los conflictos

**Gráfico carga vs capacidad:** selecciona una línea concreta o ve todas las líneas agregadas. Las barras rojas indican semanas con déficit.

**Vista temporal por proyecto (Gantt):**
- 🔴 Rojo `+Xh` — déficit en esa semana.
- 🟠 Naranja `XX%` — saturación alta sin déficit.
- 🟢 Verde `·` — sin tensión.

**Qué se rompe — por semana y línea:** tabla de conflictos con semana, línea, déficit h, carga h, capacidad h, saturación % y proyectos implicados.

### Paso 6 — Decidir qué hacer

Si hay conflictos, hay tres opciones:
- **Primera ronda:** mover el proyecto completo o ampliar semanas.
- **Revisar alternativas candidatas:** el sistema simula mover cada proyecto en conflicto a sus líneas alternativas y muestra cuáles mejoran el déficit.
- **No actuar ahora:** aceptar el conflicto y continuar.

---

## 5. PRIMERA RONDA

### 5.1 Principio fundamental: el Plan real nunca se modifica

Todas las acciones de primera y segunda ronda generan o actualizan una **Simulación activa**. El Plan real cargado desde el Excel permanece intacto siempre.

Cuando hay una Simulación activa en curso, la app muestra un banner:

> "⚠ Simulación activa — el plan real no ha cambiado. Para descartar todos los cambios, usa el botón 'Reiniciar simulación'."

Para descartar todos los cambios simulados y volver al Plan real, pulsa **"Reiniciar simulación"**.

### 5.2 Solapa 1 — Mover línea (mover proyecto completo)

Mueve el proyecto completo a una o varias líneas destino.

- Mueve **todo el proyecto**: no solo el exceso de horas.
- Si se seleccionan varias líneas destino, la carga se reparte con fracciones iguales:
  - 2 líneas destino → 50 % / 50 %
  - 3 líneas destino → aprox. 33 % / 33 % / 34 %
  - 4 líneas destino → 25 % / 25 % / 25 % / 25 %
- Preferible cuando otra línea compatible encaja mejor, porque puede evitar retrasar la entrega.

### 5.3 Solapa 2 — Ampliar semanas

Distribuye la carga del proyecto en más semanas para reducir la carga semanal.

- El proyecto ocupa más semanas → la carga por semana baja.
- Si la ampliación supera la semana de entrega objetivo, se genera aviso de impacto en entrega.
- Alternativa fuerte si no hay línea mejor disponible o si se acepta alargar la duración.

---

## 6. SEGUNDA RONDA

### 6.1 Propósito

La segunda ronda (Solapa 3 — Segunda ronda / Ajustar pendientes) permite actuar sobre los conflictos que siguen vivos después de la primera ronda. No es una planificación nueva desde cero.

### 6.2 Entrada: qué se ve

La segunda ronda trabaja exclusivamente sobre la **Simulación activa**. Solo muestra conflictos que siguen abiertos después de las acciones de primera ronda.

### 6.3 Acciones disponibles

| Acción | Cuándo usar |
|---|---|
| **Ampliar semanas en destino** | Mantener el proyecto donde está y repartir la carga en más semanas. |
| **Mover/reprogramar exceso** | Mover solo la parte sobrante del proyecto, no todo el proyecto. |
| **No actuar** | Aceptar que ese conflicto queda vivo. El sistema registra el diagnóstico. |

### 6.4 Combinar acciones sobre proyectos distintos

La segunda ronda permite combinar acciones sobre **proyectos distintos** en la misma sesión:

- Se puede ampliar semanas de un proyecto Y mover exceso de otro proyecto diferente.
- No se puede aplicar dos acciones distintas al mismo proyecto en la misma segunda ronda.

---

## 7. MOVER EXCESO / REPROGRAMAR RESIDUAL

### 7.1 Qué es el exceso

El exceso (también llamado residual) es la parte de la carga de un proyecto que contribuye al déficit de la línea origen. No es todo el proyecto: es la fracción sobrante. Dos acotaciones obligatorias:

- **No se mueve más carga que la del propio proyecto:** aunque la línea esté muy sobrecargada, el exceso del proyecto no puede superar su carga real en esa semana.
- **No hay exceso si la línea no está en déficit:** si la carga total de la línea no supera la capacidad nominal, el exceso de ese proyecto es cero aunque su carga sea alta.

```
exceso_semana_W = min(
    carga_proyecto_en_W,
    max(0, carga_total_linea_en_W − capacidad_nominal_linea_en_W)
)
```

### 7.2 Reparto entre destinos

La carga a mover se reparte con fracciones iguales entre los destinos seleccionados:

| Nº destinos | Fracción por destino |
|---|---|
| 1 | 100 % |
| 2 | 50 % / 50 % |
| 3 | aprox. 33 % / 33 % / 34 % |
| 4 | 25 % / 25 % / 25 % / 25 % |

**Las fracciones son iguales en ambos modos (Paralelo y Secuencial).** La diferencia entre los modos es temporal, no de porcentaje.

### 7.3 Modo Paralelo

El exceso se reparte entre los destinos y se coloca **en las mismas semanas donde aparece el exceso** (semanas del conflicto original).

Ejemplo: si el exceso está en S7, S8 y S9 → el destino recibe carga en S7, S8 y S9.

Cuándo usar Paralelo:
- El proyecto es un **lote divisible** (varias unidades independientes) y puede haber trabajo en paralelo en varias líneas.

### 7.4 Modo Secuencial

El exceso se reparte con las **mismas fracciones** que en Paralelo, pero se coloca **después del tramo principal del proyecto**, en cascada temporal:

```
Semana de inicio del residual = max(semanas_del_proyecto) + 1

Destino 1: empieza en max(semanas_proyecto) + 1
Destino 2: empieza donde terminó el Destino 1
Destino 3: empieza donde terminó el Destino 2
```

**La diferencia con Paralelo es temporal, no de porcentaje.** Ambos modos reparten las mismas horas entre los mismos destinos. Solo cambia cuándo se coloca esa carga.

Cuándo usar Secuencial:
- El proyecto es un **equipo único** (unidad física indivisible que no puede estar en dos líneas al mismo tiempo).
- Se quiere que el trabajo en la línea destino empiece después de terminar el tramo principal en la línea origen.

### 7.5 Aviso por tipo de proyecto

Al elegir "Mover/reprogramar exceso", la app muestra orientación según el tipo de proyecto declarado en el Excel:

| Tipo de proyecto | Aviso |
|---|---|
| Equipo único | Aviso fuerte: el equipo no puede estar en dos líneas al mismo tiempo. Se recomienda Secuencial. |
| Lote divisible | Orientación: puede ir en Paralelo si las unidades son independientes. |
| Fase transferible | Orientación: solo si la fase concreta es compatible con la línea destino. |
| Desconocido / vacío | Advertencia fuerte: no se asume divisible ni paralelo. El planificador debe validar. |

---

## 8. REGLA DE EXCLUSIVIDAD DE LÍNEA

Una línea no monta dos proyectos/modelos distintos al mismo tiempo. Cuando se coloca carga en una línea destino, la app distingue:

| Situación en la semana W | Capacidad utilizable | Comportamiento |
|---|---|---|
| Semana vacía | Capacidad nominal completa | Continúa a la semana siguiente |
| Carga del **mismo** proyecto en destino | `Capacidad nominal − carga existente del mismo proyecto` | Continúa usando el hueco |
| Primera semana con carga de **otro** proyecto/modelo | `Capacidad nominal − carga otro proyecto` | Se puede usar el hueco, pero requiere confirmación explícita (semana de transición con carga previa) |
| Segunda semana en adelante con carga de **otro** proyecto/modelo | `Capacidad nominal − carga otro proyecto` (solo el hueco libre) | **Regla C3:** se coloca `min(pendiente, hueco_libre)` y se detiene. No se salta a semanas posteriores. |
| Capacidad restante = 0 (saturación) | 0 h | Cálculo se detiene. No se coloca nada. |

**Regla C3 explicada en detalle:**
Cuando la colocación llega (desde la segunda semana del movimiento) a una semana con carga de otro proyecto/modelo, el sistema:
1. Calcula el hueco libre disponible: `capacidad_nominal − carga_otro_proyecto`.
2. Coloca `min(horas_pendientes, hueco_libre)` en esa semana.
3. Detiene la colocación.
4. No busca huecos en semanas posteriores.

Consecuencia: si esa semana tiene hueco libre, parte del exceso se absorbe antes de detenerse. Si no tiene hueco libre (saturada por el otro proyecto), no se absorbe nada y se detiene igualmente.

Cuando el cálculo se detiene (por cualquier causa), la app registra y muestra:
- Semana de bloqueo y causa (exclusividad de línea o saturación)
- Proyecto/modelo bloqueante
- Carga colocada hasta ese punto
- Carga no absorbida (nunca se pierde silenciosamente)

---

## 9. CLASIFICACIÓN DE ALTERNATIVAS Y ACCIONES

Cuando el sistema evalúa alternativas candidatas o el planificador revisa opciones en segunda ronda, cada alternativa o acción se clasifica en una de estas cuatro categorías:

| Clasificación | Qué significa |
|---|---|
| **Directa** | Se puede aplicar sin bloqueo relevante. La línea destino tiene compatibilidad y capacidad suficiente. Confirmación estándar. |
| **Revisar** | Puede mejorar el conflicto pero no lo resuelve del todo, o requiere validación operativa adicional. Puede dejar déficit vivo y requerir segunda ronda. |
| **Bloqueada** | No debe aplicarse: no hay capacidad suficiente, hay incompatibilidad de modelo/línea o hay bloqueo operativo. El sistema muestra el motivo. |
| **No aplicable** | No es adecuada para ese caso concreto dado el tipo de proyecto, la semana, la línea o el estado de la simulación. |

**Atención: "Revisar" no es solución cerrada.**
Una alternativa clasificada como "Revisar" puede reducir el déficit, pero el planificador debe verificar que el conflicto residual es aceptable. Si queda conflicto vivo tras aplicarla, debe gestionarse en segunda ronda.

**"Bloqueada" no significa invisible.**
El sistema siempre muestra la alternativa bloqueada con el motivo del bloqueo. El planificador puede ver por qué no puede usarla.

---

## 10. CÓMO INTERPRETAR LOS RESULTADOS

### 9.1 Veredicto verde

Todas las líneas, en todas las semanas, tienen carga ≤ capacidad. No hay déficit. Los proyectos excluidos (si los hay) siguen siendo una advertencia a gestionar.

### 9.2 Veredicto rojo

Al menos una línea supera su capacidad en al menos una semana. El déficit no significa que la planta no pueda producir: significa que con el plan actual hay semanas donde la demanda de horas supera las horas disponibles.

### 9.3 Proyectos implicados no son culpables únicos

Si tres proyectos tienen carga en la línea L01 la semana 22, los tres aparecen como "implicados" aunque solo uno sea el detonante que supera el límite. El análisis de qué mover requiere juicio del planificador.

### 9.4 Gantt de colores

El color refleja el estado de la **línea** en esa semana, no del proyecto en particular. Un proyecto en verde puede estar en una línea sin tensión aunque el proyecto en sí sea grande.

### 9.5 Alternativas candidatas

Son simulaciones individuales. Una candidata marcada como "Libera" significa que, si ese proyecto se moviera a esa línea, el déficit desaparecería para ese proyecto. Pueden existir efectos secundarios en la línea destino (anotados como avisos). La decisión la toma el planificador.

---

## 11. PANEL DE AUDITORÍA

El panel de auditoría es para análisis técnico. No es necesario en el uso normal.

| Sección | Cuándo revisarla |
|---|---|
| Proyectos excluidos | Cuando el KPI "Excluidos" > 0 y no se sabe por qué |
| Capacidad por línea | Para verificar que el escenario tiene la capacidad esperada |
| Carga calculada | Para confirmar el reparto semana/línea/proyecto en detalle |
| Alternativas descartadas | Para entender por qué una alternativa no fue candidata |
| Avisos | Para revisar alertas de importación del Excel |
| Conflictos completos | Para ver todos los conflictos sin filtrar |

---

## 12. LIMITACIONES ACTUALES

| Código | Limitación |
|---|---|
| L01 | **Reparto uniforme V1:** las horas se distribuyen linealmente entre semanas. No hay picos ni aceleración. |
| L02 | **Evaluación de alternativas individual:** el evaluador de alternativas candidatas (Calcular alternativas candidatas) analiza mover un proyecto a la vez, sin combinar movimientos de varios proyectos. En segunda ronda sí se pueden aplicar acciones sobre proyectos distintos en la misma sesión (commit `0d286768`). |
| L03 | **Horizonte máximo: semana 52.** Proyectos que exceden ese horizonte se recortan con aviso. |
| L04 | **Exportación pendiente:** la Simulación activa no se puede exportar todavía a Excel. |
| L05 | **Dependencia de calidad del Excel:** si `Semana inicio mínima` o `Horas totales` están vacías o mal formateadas, el proyecto queda excluido. |
| L06 | **Dependencia del escenario activo:** si el escenario no refleja la realidad operativa, la capacidad calculada puede ser incorrecta. |

---

## 13. EJEMPLO MÍNIMO END-TO-END

### Escenario de referencia

Planta ORTUELLA. Escenario activo con 4 líneas (L01–L04). Capacidad ≈ 40 h/sem por línea.

### Ejemplo 1 — Primera ronda: mover proyecto completo

**Situación:**
- PRY-001 en L01 (30 h/sem), semanas 10–14.
- PRY-002 en L01 (25 h/sem), semanas 12–16.
- Semanas 12–14: 30 + 25 = 55 h/sem en L01 → déficit 15 h/sem × 3 semanas = 45 h.

**Acción:** mover PRY-002 a L02 (que tiene capacidad disponible en semanas 12–16).

**Resultado:** veredicto verde. PRY-002 en L02, sin conflicto.

### Ejemplo 2 — Segunda ronda: mover exceso

**Situación tras primera ronda:**
- PRY-003 en L01, 60 h/sem durante semanas 18–22. Capacidad L01 = 40 h/sem.
- Déficit: 20 h/sem × 5 semanas = 100 h de exceso.

**Acción en segunda ronda:** mover exceso en modo Secuencial a L03.

**Cálculo:** PRY-003 termina en semana 22 → residual empieza en semana 23 en L03.
100 h repartidas en L03 a partir de S23, semanas consecutivas, respetando la capacidad disponible de L03.

**Resultado:** las semanas 18–22 en L01 siguen con déficit (no se eliminan, solo se gestiona el exceso). El residual en L03 aparece a partir de S23 en la Simulación activa.

### Ejemplo 3 — Segunda ronda: ampliar semanas

**Situación:**
- PRY-004 en L02, 80 h/sem durante 3 semanas (S8–S10). Capacidad L02 = 40 h/sem.
- Déficit: 40 h/sem × 3 semanas = 120 h.

**Acción en segunda ronda:** ampliar de 3 a 6 semanas (S8–S13).

**Cálculo:** 240 h totales / 6 semanas = 40 h/sem → igual a la capacidad. Sin déficit.

**Resultado:** sin déficit en L02 S8–S13. Si S13 supera la semana de entrega objetivo → aviso de retraso.

---

## 14. FLUJO VISUAL RESUMIDO

```
CARGAR EXCEL
    ↓
VERIFICAR ESCENARIO ACTIVO
    ↓
CALCULAR PROGRAMACIÓN REAL
    ↓ (si hay conflictos)
PRIMERA RONDA
    → Mover proyecto completo (Solapa 1)
    → Ampliar semanas (Solapa 2)
    ↓ (si siguen conflictos)
SEGUNDA RONDA (Solapa 3)
    → Ampliar semanas en destino
    → Mover exceso (Paralelo o Secuencial)
    → No actuar
    ↓
REVISAR SIMULACIÓN ACTIVA
    ↓ (si hay que descartar)
REINICIAR SIMULACIÓN → vuelve al Plan real
```

---

*Fin del documento — Manual de Usuario Programación real v0.5 (junio 2026)*
