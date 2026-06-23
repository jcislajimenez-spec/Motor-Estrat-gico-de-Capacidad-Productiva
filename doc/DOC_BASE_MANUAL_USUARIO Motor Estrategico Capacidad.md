# DOCUMENTO BASE — Manual de Usuario
## Motor Estratégico de Capacidad Productiva
### INGETEAM — Versión de referencia: mayo 2026

---

> **Propósito de este documento:** Base de conocimiento estructurada y actualizada para redactar un manual de usuario profesional y construir una presentación ampliada de 10–12 slides. Refleja el estado real de la aplicación en staging/producción (abril 2026). No es el manual final; es el documento maestro que lo alimenta.

---

## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Qué es

El **Motor Estratégico de Capacidad Productiva** es una aplicación web interna de INGETEAM desarrollada en Python/Streamlit. Su función es calcular, visualizar y comparar la **capacidad productiva real** de las plantas de fabricación de la compañía, enfrentándola contra la demanda planificada, tanto a nivel semanal como a lo largo del año completo.

No es un ERP ni un MES. Es una herramienta de **análisis y toma de decisiones estratégicas** a nivel de capacidad. Permite responder preguntas del tipo:
- ¿Puede la planta X producir Y unidades del modelo Z esta semana?
- ¿Cuál es el cuello de botella real, a nivel de proceso?
- ¿Qué ocurre si cambia el mix de modelos?
- ¿Puede la planta absorber la demanda prevista el año completo? ¿Cuándo hay tensión? ¿Cuándo hay déficit?

### 1.2 Usuarios objetivo

| Perfil | Uso principal |
|--------|--------------|
| **Planificador / Responsable de producción** | Planificación, Resultados y Simulación anual. Introduce demanda, selecciona modelos y escenarios, lee la tabla resumen, los gráficos y la simulación anual. |
| **Power user / Ingeniero de procesos** | Configuración. Mantiene tiempos de ciclo, estaciones, operarios, compatibilidades y configuración de bancos de prueba. |
| **Dirección / Estrategia** | Global (visión multiplanta), Capacidad según mix y Simulación anual para lectura ejecutiva de riesgo y saturación anual. |

### 1.3 Plantas gestionadas

Cada planta tiene sus propios parámetros operativos (turnos, disponibilidad, eficiencia, días), sus propias líneas, modelos compatibles y tiempos de proceso. Los datos son **independientes por planta** (arquitectura multi-tenant con `plant_id`).

Plantas habituales en el sistema:
- SESMA, ORTUELLA, CHENNAI, MILWAUKEE, ELECTRONICS, CAMPINAS, BEASÁIN

Pueden añadirse nuevas plantas desde el propio sidebar de la aplicación.

### 1.4 Tecnología

- **Frontend/Backend:** Python + Streamlit 1.54
- **Motor de cálculo:** `engine.py` (Python/Pandas)
- **Persistencia:** Base de datos PostgreSQL (Neon) con fallback a CSV locales en `./data/`
- **Visualización:** Plotly (gráficos interactivos)
- **Despliegue:** Accesible vía navegador web (Render / red corporativa)
- **Internacionalización:** Selector de idioma en sidebar (ES / EN / EU)

---

## 2. ESTRUCTURA DE LA APLICACIÓN

### 2.1 Layout general

La interfaz se divide en dos zonas:

```
┌─────────────────┬────────────────────────────────────────────────────────────┐
│   SIDEBAR       │   ÁREA PRINCIPAL (navegación por tabs)                     │
│                 │                                                            │
│ [🌙 Modo oscuro]│  🌐 Global  │  📊 Planificación  │  ⚙️ Configuración      │
│ [🌍 Idioma    ] │  📈 Resultados  │  🧭 Cap. según mix  │  📅 Simulación anual│
│                 │                                                            │
│ Logo Ingeteam   │  (contenido del tab activo)                                │
│                 │                                                            │
│ Seleccionar     │                                                            │
│ planta          │                                                            │
│                 │                                                            │
│ [Nueva planta]  │                                                            │
│                 │                                                            │
│ Parámetros de   │                                                            │
│ planificación   │                                                            │
│                 │                                                            │
│ [Guardar params]│                                                            │
└─────────────────┴────────────────────────────────────────────────────────────┘
```

### 2.2 Sidebar (siempre visible)

El sidebar es el **panel de control global** de la sesión. Contiene, de arriba a abajo:

**A) Controles de interfaz (franja superior, compacta)**
- **Modo oscuro:** checkbox que activa/desactiva el tema oscuro de la aplicación
- **Idioma:** selector entre ES (español), EN (inglés), EU (euskera)
- Ambos controles se guardan por sesión y no afectan a los datos ni al cálculo

**B) Logo Ingeteam**

**C) Selector de planta**
- Dropdown con todas las plantas disponibles en la BD
- Cambia el contexto de toda la aplicación (tabs 1–5)
- La selección **no** afecta al Tab Global, que muestra siempre todas las plantas
- Campo de texto y botón para añadir nuevas plantas directamente desde el sidebar

**D) Parámetros de planificación** (por planta)
- Horas por semana (numérico, ej: 48.80 h/sem)
- Turnos (número entero ≥ 1)
- Disponibilidad (slider 0.0–1.0)
- Eficiencia (slider 0.0–1.0)
- Días abiertos al año (entero)
- Días abiertos por semana (entero, 1–7)

**E) Cálculos derivados mostrados en tiempo real**
- Horas efectivas planta = `horas/sem × turnos × disponibilidad × eficiencia`
- Semanas equivalentes = `días_año / días_semana`

**F) Botón "Guardar parámetros de esta planta"**
Persiste los parámetros en base de datos para la planta activa.

### 2.3 Tabs (pestañas principales)

| # | Nombre | Perfil principal | Descripción corta |
|---|--------|-----------------|-------------------|
| 0 | 🌐 Global | Dirección / Todos | Visión multiplanta simultánea |
| 1 | 📊 Planificación | Planificador | Selección de modelo, variante y demanda por línea. Gestión de escenarios. |
| 2 | ⚙️ Configuración | Ingeniero (Power User) | Mantenimiento de datos maestros |
| 3 | 📈 Resultados | Planificador / Dirección | Tabla resumen + detalle fino + overrides + bancos + gráficos |
| 4 | 🧭 Capacidad según mix | Estrategia | Análisis de rango estructural y simulador de ocupación |
| 5 | 📅 Simulación anual | Planificador / Dirección | Simulación anual de capacidad vs demanda con lectura ejecutiva |
| 6 | 📋 Programación real | Planificador / Producción / Ingeniería | Carga proyectos reales desde Excel, reparte horas por semanas y detecta conflictos de capacidad por semana, línea y proyecto |

---

## 3. DESCRIPCIÓN DE PANTALLAS

### 3.1 TAB 0 — Visión Global Multiplanta

**Propósito:** Comparar todas las plantas simultáneamente en un solo vistazo, sin necesidad de cambiar el selector de planta.

**Aviso informativo:** "Esta vista muestra información agregada de TODAS las plantas simultáneamente, independiente del selector de planta del sidebar."

#### 3.1.1 Selector de Escenario

- **Escenario de capacidad:** radio button entre Máximo / Promedio / Mínimo
  - Máximo: capacidad con el modelo más favorable por línea
  - Promedio: media de todos los modelos compatibles
  - Mínimo: capacidad con el modelo más desfavorable
- **Turnos (simulación global):** radio button entre Config. actual / 1 turno / 2 turnos / 3 turnos

#### 3.1.2 Resumen Global de Capacidad

Tabla con una fila por planta. Columnas:

| Columna | Descripción |
|---------|-------------|
| Planta | Nombre de la planta |
| Nº líneas | Líneas activas con datos |
| CAP (UDS/sem) | Capacidad en unidades/semana (escenario seleccionado) |
| CAP (UDS/año) | Capacidad en unidades/año |
| CAP (h/sem) | Capacidad en horas/semana |
| CAP (h/año) | Capacidad en horas/año |
| Fila TOTAL | Suma de todas las plantas |

#### 3.1.3 Capacidad vs Disponibilidad por Planta

Gráfico de barras agrupadas (Plotly): Capacidad (rojo Ingeteam) vs Disponibilidad (azul) en h/año por planta. Tabla interactiva donde el usuario puede introducir la disponibilidad anual real de cada planta y ver el % de utilización resultante (verde < 80%, ámbar 80–99%, rojo ≥ 100%).

#### 3.1.4 Capacidad por Modelo

Selector de modelo (dropdown) → tabla por planta mostrando capacidad en uds/sem, uds/año, h/sem, h/año para ese modelo. Solo aparecen plantas donde el modelo es compatible con alguna línea.

#### 3.1.5 Distribución de Capacidad por Planta

Gráfico de tarta/donut: distribución porcentual de la capacidad total (en h/año) entre plantas.

#### 3.1.6 Uso de Líneas por Planta

Tabla resumen del número de líneas activas y configuradas por planta.

#### 3.1.7 Modificaciones Necesarias

Panel de registro de mejoras planificadas (hitos de inversión/mejora): título, planta, horas estimadas. Botón para añadir y eliminar. Resumen de hitos y horas totales. Es informativo — no se conecta al motor de cálculo.

---

### 3.2 TAB 1 — Planificación

**Propósito:** El planificador selecciona qué modelo (y variante de prueba para equipos D&A) produce cada línea y cuántas unidades necesita.

**Contexto:** Actúa sobre la planta activa en el sidebar. Los datos se persisten en session_state por planta.

#### 3.2.1 Selección de modelo y demanda por línea

La interfaz organiza las líneas por nave (ej: NAVE N1, NAVE N2). Por cada línea dentro de la nave se muestran tres columnas:

| Columna | Contenido |
|---------|-----------|
| Línea | Código de la línea (ej: N1-L01) |
| Modelo / Variante de prueba | Dropdown combinado con las opciones compatibles |
| Demanda (UDS/SEM) | Campo numérico de demanda semanal |

**Dropdown combinado (Modelo · Variante):**
- Para modelos no D&A: muestra solo el nombre del modelo (ej: `PT0163`)
- Para familias D&A (SL, SD, LL, LD, XD, XL): muestra el modelo y la variante de banco de prueba como una sola opción combinada (ej: `SL · LV`, `SL · MV`, `LL · LV`, etc.)
- La variante de prueba (LV o MV) determina qué tipo de banco se asigna a esa línea en el análisis de bancos de Resultados
- Si no se especifica variante, se aplica la regla general configurada para esa familia

#### 3.2.2 Gestión de escenarios

Bajo la tabla de líneas, el panel de gestión de escenarios permite:

- **Selector de escenario activo:** dropdown con los escenarios guardados para esta planta. El activo actual se marca con `★ Activo`.
- **Botones de acción:**
  - **Cargar:** carga la planificación (modelos + demandas) del escenario seleccionado
  - **Duplicar:** crea una copia del escenario seleccionado con nuevo nombre
  - **Guardar cambios:** persiste los cambios actuales en el escenario activo
  - **Guardar como nuevo:** crea un nuevo escenario con la planificación actual
  - **Eliminar:** borra el escenario seleccionado (con confirmación)
- **Campo de nombre:** permite renombrar el escenario antes de guardar
- El escenario activo es el que usan Resultados y Simulación anual cuando se navega entre pestañas

**Persistencia del escenario activo entre pestañas:**
El escenario seleccionado en Planificación persiste de forma estable en memoria de sesión. Si el usuario navega a Resultados o Simulación anual y vuelve, el escenario sigue siendo el mismo.

---

### 3.3 TAB 2 — Configuración (Power User)

**Propósito:** Mantenimiento de los datos maestros del sistema.

**Aviso:** "Aquí se mantienen modelos, tiempos, estaciones y compatibilidades. Usuario normal NO debería tocar esto."

#### 3.3.1 Gestión de modelos

Tabla editable con columnas: `model`, `description`, `active`. El campo `active` controla si el modelo aparece en Planificación y en los dropdowns de compatibilidades. Botón **"💾 Guardar modelos"**.

#### 3.3.2 Tiempos por modelo y proceso

Tabla editable con columnas: `model`, `process`, `cycle_time` (legacy), `machine_time`, `labor_time`. Filtros por modelo y por proceso para facilitar la edición.

**Bloque explicativo visible al usuario:**
> Machine time = tiempo automático fijo no reducible (test automático, horno, robot, ciclo máquina). No depende del nº de operarios.
> Labor time = horas-hombre secuenciales necesarias por unidad (preparación, conexión, montaje manual, supervisión, retirada).
> `cycle_time_real = max(machine_time, labor_time / operarios)` → `capacity = (horas_efectivas × estaciones) / cycle_time_real`

Botón **"💾 Guardar tiempos"**.

#### 3.3.3 Configuración de estaciones y operarios

Tabla editable con columnas: `line`, `nave`, `line_id`, `process`, `stations`, `operators_per_station`. Filtro por proceso. Botón **"💾 Guardar estaciones / operarios"**.

#### 3.3.4 Compatibilidad modelo ↔ línea

Sección expandible por línea con checkboxes por modelo. Un modelo marcado = ese modelo puede producirse en esa línea. Botones **"Desplegar todas"** / **"Plegar todas"** y exportación a Excel. Botón **"💾 Guardar compatibilidades"**.

#### 3.3.5 Bancos de prueba

Sección exclusiva para plantas con líneas de Diagnóstico y Análisis (D&A).

**Bancos disponibles por tipo:**
Tabla con columnas `Tipo de banco` y `Cantidad de bancos`. Define cuántos bancos LV y cuántos bancos MV tiene disponibles la planta.

**Asignación valor D&A → tipo de banco:**
Tabla con columnas `Valor D&A en el motor`, `Variante de prueba` y `Banco aplicable`. Permite asignar a cada familia D&A (SL, SD, LL, LD, XD, XL) y a cada variante (LV, MV) el tipo de banco que le corresponde.

> Nota: Esta asignación es una simplificación operativa de esta fase. Dentro de una misma familia puede haber equipos con prueba LV y equipos con prueba MV. La variante seleccionada en Planificación por línea refina esta asignación general.

Botones: **"💾 Guardar bancos"** y **"💾 Guardar asignación D&A"**.

---

### 3.4 TAB 3 — Resultados

**Propósito:** Ver los resultados de capacidad para la planta activa, con la planificación del escenario activo.

#### 3.4.1 Panel ejecutivo de resumen

Métricas rápidas al inicio de la pantalla:
- **Líneas con déficit**
- **Saturación máxima (%)**
- **Líneas ≥ 90% saturación**
- **Cuello principal** (proceso más limitante del conjunto)

Nota informativa: "Tabla ordenada por criticidad: déficit primero, luego alta saturación."

#### 3.4.2 Tabla resumen de resultados

Una fila por línea activa con modelo seleccionado. Columnas:

| Columna | Descripción |
|---------|-------------|
| nave | Nave física |
| line | Código de línea |
| model | Modelo seleccionado |
| Demanda (UDS/SEM) | Demanda introducida en Planificación |
| Capacidad (UDS/SEM) | Capacidad calculada (cuello de botella) |
| Saturación (%) | Demanda / Capacidad × 100. Rojo ≥ 100%, verde < 100% |
| Déficit (UDS/SEM) | max(0, Demanda − Capacidad) |
| bottleneck | Proceso cuello de botella (rojo negrita) |
| Demanda / Capacidad (UDS/AÑO) | Anualización |
| Demanda / Capacidad (h/SEM) | Conversión a horas |
| Demanda / Capacidad (h/AÑO) | Conversión a horas anualizada |

Fila TOTAL al final con sumas. Botón **"⬇️ Exportar a Excel"**.

#### 3.4.3 Comparativa entre escenarios

Dropdown de selección de escenario de comparación. Cuando se selecciona un segundo escenario, se genera una tabla comparativa de diferencias y un botón **"⬇️ Exportar comparativa a Excel"**.

#### 3.4.4 Parámetros por línea (overrides)

Panel expandible "⚙ Parámetros por línea". Permite ajustar para cada línea individualmente:
- **Override activado:** checkbox que habilita los parámetros específicos de esa línea
- **Turnos**, **Disponibilidad**, **Eficiencia**: valores propios de la línea, independientes de los globales del sidebar
- **Turnos por proceso:** ajuste más fino — permite definir turnos distintos por proceso dentro de una misma línea (mediante popover)
- Botón **"💾 Guardar parámetros por línea"** — persiste en BD ligado al escenario activo

Los overrides por línea permiten modelar situaciones reales: una línea que trabaja a 2 turnos mientras el resto trabaja a 1, o una línea con una disponibilidad reducida por mantenimiento.

#### 3.4.5 Personas equivalentes (FTE informativo)

Panel informativo que calcula el número de personas equivalentes necesarias para ejecutar el plan actual. No representa plantilla asignada ni FTE confirmados; es una estimación funcional basada en las horas de proceso y los parámetros de la planta.

#### 3.4.6 Detalle fino por línea y subproceso

Expandibles colapsados por defecto, uno por línea. Dentro: tabla con `process`, `stations`, `operators_per_station`, `machine_time`, `labor_time`, `labor_per_operator`, `cycle_time_real`, `capacity`. La fila del proceso cuello de botella se resalta en rojo.

#### 3.4.7 Análisis de bancos de prueba (D&A)

Para plantas con líneas D&A y bancos configurados en Configuración. Muestra:

- **Tabla individual por línea D&A:** demanda (UDS/SEM), horas de prueba demandadas, bancos disponibles del tipo asignado y saturación del banco
- **Resumen agregado por tipo de banco:** agrega todas las líneas que usan el mismo tipo de banco (LV o MV) y compara horas disponibles vs horas demandadas en conjunto
  - Horas disponibles/sem: horas_efectivas × nº bancos del tipo
  - Horas demandadas/sem: suma de demanda × tiempo prueba PARA por línea
  - Saturación global del conjunto de bancos

> Este bloque es informativo y no modifica la lógica oficial del motor (capacidad, saturación, déficit ni cuello de botella).

#### 3.4.8 Gráficos de Demanda vs Capacidad

Cuatro gráficos de barras agrupadas (Plotly):
1. Demanda vs Capacidad — UDS/SEM
2. Demanda vs Capacidad — h/SEM *(marcado como crítico)*
3. Demanda vs Capacidad — UDS/AÑO
4. Demanda vs Capacidad — h/AÑO *(marcado como crítico)*

Los gráficos en horas son los más relevantes para detectar sobrecarga real de personal. Eje X = líneas de producción.

---

### 3.5 TAB 4 — Capacidad según mix

**Propósito:** Análisis estratégico de la capacidad como **rango estructural**, no como valor fijo. Responde a: "¿cuánto puede producir la planta dependiendo del mix de modelos?"

#### 3.5.1 Nivel 1 — Global planta (rango estructural)

Tabla de 3 filas (Máximo / Promedio / Mínimo) con columnas UDS/SEM, UDS/AÑO, h/SEM, h/AÑO. El máximo es la suma de las capacidades máximas independientes por línea.

#### 3.5.2 Nivel 2 — Por línea (rango estructural)

Tabla con una fila por línea: nave, línea, modelo que genera capacidad máxima en horas, modelo que genera mínimo, y los valores Max/Prom/Min en UDS y horas.

#### 3.5.3 Nivel 3 — Simulador de ocupación estructural por modelo

Por modelo: slider "Ocupación simulada (% de planta)" + equivalencias (uds/sem, uds/año, h/sem, h/año) + gráfico donut.

Agregado planta: techo estructural H_max_plant, velocímetro (gauge) con el % total ocupado (verde hasta 100%, rojo si excede), gráfico de barras apiladas horizontal con distribución por modelo, métricas de horas y unidades equivalentes.

> **Aviso:** Este simulador NO cambia la planificación real. Solo sirve para explorar cuánto 'peso' estructural podría llegar a ocupar cada modelo.

---

### 3.6 TAB 5 — Simulación anual

**Propósito:** Simular la capacidad de la planta frente a la demanda prevista a lo largo de las 52 semanas del año. Conecta la previsión de negocio con la capacidad productiva definida en el escenario activo, y genera una lectura ejecutiva de riesgo, saturación y déficit anual.

Esta funcionalidad representa un avance significativo respecto a la lectura semanal estructural: permite responder preguntas como "¿hay semanas del año donde no podemos cubrir la demanda?", "¿cuándo es el pico de tensión?" o "¿cuál es el déficit acumulado anual?".

#### 3.6.1 Condiciones previas

Para acceder al cálculo de simulación es necesario:
1. Tener un **escenario activo** definido en Planificación con modelos asignados a las líneas
2. Disponer de un **Excel de simulación anual** con los datos de demanda por modelo y semana

Si no hay escenario activo o no hay líneas planificadas, la pestaña muestra avisos claros e informativos antes de continuar.

#### 3.6.2 Capacidad base de planta (referencia)

Al acceder a la pestaña, se muestra de forma automática la capacidad base de la planta en h/sem calculada a partir del escenario activo:

- **h/sem por línea (global):** horas efectivas por línea, promediadas
- **Líneas planificadas:** número de líneas con modelo asignado
- **Cap. base planta (h/sem):** capacidad base total de la planta, calculada con la misma lógica que Resultados (incluye overrides por línea y por proceso si están configurados)

> Nota: Este valor es la base real del escenario activo, no una hipótesis simplificada. Aplica los overrides individuales por línea y los ajustes de proceso definidos en Resultados.

#### 3.6.3 Plantilla descargable

Botón **"⬇️ Descargar plantilla Excel"** que genera y descarga una plantilla con la estructura esperada por el parser, lista para rellenar.

La plantilla contiene 4 hojas:

| Hoja | Contenido |
|------|-----------|
| **DEMANDA_HORAS** | Una fila por modelo, columnas Sem 1…Sem 52 con las horas de demanda previstas por semana |
| **PLAN_HORAS** | Misma estructura que DEMANDA_HORAS. Representa el plan de producción comprometido (opcional). |
| **SEMANAS_ESPECIALES** | Columnas: `semana`, `horas_disponibles`, `motivo`. Permite definir semanas con capacidad diferente a la base (ej: parada de verano, semana reducida). |
| **RESUMEN_SEMANAL** | Hoja de referencia con estructura de métricas semanales (solo orientativa). |

#### 3.6.4 Carga y validación del Excel

El usuario sube el Excel rellenado mediante el componente de subida de archivos. El sistema realiza una validación en dos niveles:

**Validaciones bloqueantes (impiden el cálculo):**
- Hoja DEMANDA_HORAS ausente
- DEMANDA_HORAS sin columna `Modelo`
- DEMANDA_HORAS sin columnas `Sem 1`…`Sem 52` (se indica exactamente cuáles faltan)
- DEMANDA_HORAS vacía (sin filas de datos)
- Para calcular, las 52 semanas deben estar presentes — no se completan semanas ausentes con 0

**Validaciones no bloqueantes (avisos informativos):**
- PLAN_HORAS ausente → se usará DEMANDA_HORAS como plan de referencia
- SEMANAS_ESPECIALES ausente
- SEMANAS_ESPECIALES con columnas faltantes
- RESUMEN_SEMANAL ausente
- Celdas con valores no numéricos en columnas de semana → se convierten a 0 con aviso

Tras la validación se muestra un **resumen de lectura**: número de modelos leídos, semanas detectadas, y presencia/ausencia de cada hoja opcional.

#### 3.6.5 Cálculo de la simulación

El cálculo no se ejecuta automáticamente al subir el archivo. Se realiza de forma explícita mediante el botón **"Calcular simulación anual"**, que solo aparece cuando el archivo es apto para simular (52 semanas completas, sin errores bloqueantes).

**Cálculo semanal para cada semana w (1–52):**

| Variable | Cálculo |
|----------|---------|
| `demanda_w` | Suma de DEMANDA_HORAS[Sem w] para todos los modelos |
| `plan_w` | Suma de PLAN_HORAS[Sem w] si existe; si no, `demanda_w` |
| `cap_base_w` | Capacidad base de planta (`_sim_cap_h_sem`) |
| `cap_disponible_w` | `horas_disponibles` de SEMANAS_ESPECIALES si esa semana está definida; si no, `cap_base_w` |
| `saturacion_w` | `demanda_w / cap_disponible_w × 100` (0 si cap = 0) |
| `deficit_w` | `max(0, demanda_w − cap_disponible_w)` |

**Estado semanal (asignado por este orden de prioridad):**

| Estado | Condición |
|--------|-----------|
| ⚫ Parada | `cap_disponible_w == 0` |
| 🔴 Déficit | `cap_disponible_w > 0` y `deficit_w > 0` |
| 🟡 Atención | `deficit_w == 0` y `saturacion_w ≥ 90%` |
| 🟢 OK | Resto de casos |

El resultado se persiste en memoria de sesión y sobrevive a cambios de pestaña. Si el usuario sube un nuevo archivo, el resultado anterior se invalida automáticamente (detección por hash SHA-256 del contenido del archivo).

#### 3.6.6 Lectura ejecutiva de resultados

Tras el cálculo, la pantalla muestra:

**Banda de 5 KPIs:**

| KPI | Descripción |
|-----|-------------|
| Semanas con déficit | Número de semanas con déficit real (excluye semanas de Parada) |
| Déficit acumulado (h) | Suma del déficit semanal en horas, a lo largo del año completo |
| Semana pico | Semana con mayor saturación (excluye semanas de Parada) |
| Saturación máxima (%) | Saturación más alta registrada en el año |
| Saturación media (%) | Saturación media solo sobre semanas con capacidad > 0 |

**Nota sobre Parada:** las semanas de Parada no contaminan los KPIs de frecuencia ni de saturación media, pero sí contribuyen al déficit acumulado si hay demanda prevista para esas semanas.

**Caption de referencia:** una línea informativa con la capacidad base de planta (en h/sem) y el número de semanas con capacidad reducida por SEMANAS_ESPECIALES.

**Gráfico principal de la simulación:**
- Barras verticales de **Demanda (h)** coloreadas por estado (azul OK, ámbar Atención, rojo Déficit, gris Parada)
- Línea escalonada de **Capacidad disponible (h)** en gris antracita
- Marcadores `x` negros sobre y=0 en semanas de Parada
- Tooltip completo al pasar el ratón: Semana, Demanda, Plan, Cap. disponible, Saturación, Déficit, Estado
- Eje X: semanas 1–52 (etiquetas cada 4 semanas)
- Eje Y: horas

**Tabla semanal detallada (52 filas):**

| Semana | Demanda (h) | Plan (h) | Cap. disponible (h) | Saturación (%) | Déficit (h) | Estado |
|--------|-------------|----------|---------------------|----------------|-------------|--------|

---

### 3.7 TAB 6 — Programación real

> **Documentación detallada:** la descripción completa del módulo, incluyendo reglas de simulación, modos Paralelo/Secuencial, regla de exclusividad de línea y clasificación de alternativas, se encuentra en el documento independiente **`DOC_BASE_MANUAL_USUARIO Programacion Real.md`** (versión junio 2026, v0.5). Este apartado ofrece una visión de conjunto suficiente para el manual general del Motor Estratégico.

#### 3.7.1 Propósito

**Programación real** responde a una pregunta concreta: *¿el plan de proyectos que tenemos comprometido cabe en la capacidad de la planta, semana a semana y línea a línea?*

No es un ERP, ni un MRP, ni un secuenciador automático. No asigna operarios, no calcula materiales, no genera órdenes de fabricación. Es una **capa de decisión** que pone en contacto la lista real de proyectos (cargada desde Excel) con la capacidad calculada del escenario activo, y responde:

- ¿El plan cabe?
- ¿Dónde se rompe? ¿En qué semana? ¿En qué línea?
- ¿Cuántas horas faltan?
- ¿Qué proyectos están implicados en el conflicto?
- ¿Hay alguna alternativa candidata de línea?
- ¿Qué proyectos quedan fuera del cálculo y por qué?

Lo que **no pretende resolver:**
- No optimiza la secuencia de proyectos.
- No calcula el estado real de materiales.
- No aplica cambios automáticamente sin confirmación del usuario.
- No combina automáticamente movimientos de varios proyectos para resolver el déficit de forma conjunta.

#### 3.7.2 Condiciones previas

Antes de usar este módulo deben estar cubiertas cuatro condiciones:

1. **Escenario activo configurado en Planificación:** con modelos asignados a las líneas que se quieren analizar.
2. **Líneas con modelo asignado:** solo las líneas con modelo generan capacidad calculable.
3. **Capacidad calculable para esas líneas:** los parámetros de planta (turnos, disponibilidad, eficiencia, tiempos de proceso) deben estar cargados en la BD.
4. **Excel con hoja PROGRAMACION_REAL:** la hoja debe existir en el libro y tener las columnas obligatorias.

Si alguna condición no se cumple, la app muestra un aviso específico antes de continuar.

#### 3.7.3 Estructura del Excel PROGRAMACION_REAL

El Excel debe contener una hoja llamada exactamente `PROGRAMACION_REAL` (nombre en mayúsculas, sin acento). Una fila = un proyecto.

**Columnas obligatorias** (el parser las valida y detiene si faltan):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Proyecto` | Texto | Nombre o código identificador del proyecto. Obligatorio y único por fila. |
| `Modelo / familia` | Texto | Familia de producto o modelo (ej: PT0163, SL, GW). Se usa para trazabilidad; no determina la línea. |
| `Cantidad` | Numérico | Número de unidades del proyecto. Informativo en esta versión. |
| `Semana inicio mínima` | Entero 1–52 | Primera semana en que el proyecto puede empezar a cargarse. |
| `Semana entrega objetivo` | Entero 1–52 | Semana límite de entrega. Se usa para generar aviso si la duración calculada la supera. |
| `Horas totales` | Numérico ≥ 1 | Total de horas de trabajo del proyecto que se repartirán entre sus semanas activas. |
| `Prioridad` | Numérico | Orden de prioridad (menor = más prioritario). Se usa para ordenar la vista temporal. |

**Columnas opcionales** (si no están presentes, se rellenan con valores por defecto):

| Columna | Valor por defecto | Descripción |
|---------|-------------------|-------------|
| `Duración semanas` | Calculada automáticamente | Número de semanas de duración. Si está vacía o ausente, se calcula como `Semana entrega objetivo − Semana inicio mínima + 1`. |
| `Línea preferente` | `""` (vacío) | Código de la línea donde preferentemente se ejecuta el proyecto. Debe coincidir con los IDs de línea del escenario. |
| `Líneas alternativas` | `""` (vacío) | Líneas candidatas separadas por coma o punto y coma (ej: `L01, L02`). Se usan en el análisis de alternativas. |
| `Estado materiales` | `OK` | Estado de los materiales. Si no es OK/SI/YES, se genera un aviso pero el cálculo continúa. |
| `Estado proyecto` | `""` | Estado del proyecto (informativo). No afecta al cálculo. |
| `Cliente / referencia` | `""` | Cliente o referencia interna (trazabilidad). |
| `Código proyecto/equipo` | `""` | Código alternativo del proyecto (trazabilidad). |
| `Equipo / modelo` | `""` | Identificador específico del equipo dentro del proyecto (trazabilidad). |
| `Comentarios` | `""` | Comentarios libres (trazabilidad). |

**Aliases industriales aceptados** (se detectan y renombran automáticamente, con aviso en auditoría):

| Si el Excel trae... | Se interpreta como |
|---------------------|-------------------|
| `Codigo`, `CODIGO`, `Código`, `CÓDIGO` | `Proyecto` |
| `CLIENTE` | `Cliente / referencia` |
| `GAMA` | `Modelo / familia` |
| `EQUIPO` | `Equipo / modelo` |
| `TOTAL` | `Horas totales` |
| `ESTADO EQUIPO` | `Estado proyecto` |
| `COMENTARIOS` | `Comentarios` |

También se acepta `Código proyecto/equipo` como fuente de `Proyecto` si la columna `Proyecto` no está presente.

#### 3.7.4 Flujo de uso en pantalla

La pantalla se organiza en bloques verticales que se van completando de arriba a abajo:

**Bloque 1 — Cabecera y flujo 1–6**

Un título y una línea visual con los 6 pasos del proceso: `Cargar Excel → Validar datos → Repartir carga → Cruzar capacidad → Detectar conflictos → Proponer alternativas`. Es orientativo; los pasos suceden automáticamente al pulsar el botón de cálculo.

**Bloque 2 — Franja de carga y contexto**

Franja compacta con tres elementos en paralelo:
- **Uploader de Excel:** arrastra o selecciona el archivo `.xlsx`. El sistema detecta automáticamente si el archivo cambió (por hash SHA-256) e invalida el resultado anterior.
- **Estado de validación:** indica si el archivo está pendiente, validado correctamente (`✓ N proyectos`) o con error. Si hay avisos no bloqueantes (por ej. columnas opcionales ausentes), se muestra el número de avisos.
- **Contexto del escenario:** escenario activo, nombre de la planta, número de líneas planificadas y capacidad total en h/sem. Permite verificar que se está calculando contra el escenario correcto antes de pulsar calcular.
- **Botón "Calcular programación real":** aparece cuando hay un Excel válido cargado y hay capacidad calculada. Solo al pulsarlo se ejecuta el reparto y la detección de conflictos.
- **Enlace "⬇️ Plantilla Excel":** descarga una plantilla `.xlsx` con la estructura correcta y tres proyectos de ejemplo para orientar al usuario.

**Bloque 3 — Veredicto y KPIs**

Tras el cálculo, aparece un mensaje ejecutivo destacado:
- 🔴 **Resultado con conflictos:** "Se detectan conflictos de capacidad. Primera semana crítica: N. Línea más tensionada: X. Déficit acumulado: Y h."
- 🟡 **Sin conflictos pero con proyectos excluidos:** aviso con número de proyectos fuera.
- 🟢 **El plan cabe:** confirmación de que todos los proyectos calculados tienen capacidad.

Bajo el veredicto, una fila de 5 KPIs compactos:

| KPI | Descripción |
|-----|-------------|
| Excluidos | Proyectos sin línea resuelta o no calculables |
| Semanas conflicto | Número de semanas con déficit en alguna línea |
| Primera crítica | Primera semana en que se detecta déficit |
| Déficit total h | Suma del déficit en horas en todas las semanas/líneas |
| Línea más tensionada | Línea con mayor déficit acumulado |

**Bloque 4 — Gráfico carga vs capacidad**

Gráfico de barras interactivo (Plotly). El usuario puede seleccionar una línea concreta o ver todas las líneas agregadas. Las barras muestran la carga programada semana a semana; la línea de puntos verde muestra la capacidad disponible. Las barras rojas indican semanas con déficit. Al pasar el ratón: carga, capacidad, saturación y déficit de esa semana.

**Bloque 5 — Alternativas candidatas de línea**

Solo aparece si hay conflictos detectados. Al pulsar **"Calcular alternativas candidatas"**, el sistema evalúa individualmente cada proyecto en conflicto: simula qué pasaría si ese proyecto se moviera a cada una de sus líneas alternativas declaradas, y calcula si el déficit global mejora.

La tabla de resultados muestra: proyecto, línea actual, línea candidata, resultado (Libera / Reduce), mejora en horas y avisos (ej: modelo incompatible con la línea candidata, nuevos conflictos generados en otra línea).

**Importante:** las alternativas son propuestas de revisión, no cambios aplicados. El planificador decide si mover o no el proyecto.

**Bloque 6 — Vista temporal por proyecto (Gantt)**

Tabla pivot con una fila por proyecto y una columna por semana calculada. Cada celda muestra el estado de la línea en esa semana para ese proyecto:
- 🔴 Rojo `+Xh` — la línea tiene déficit en esa semana.
- 🟠 Naranja `XX%` — la línea supera el 90% de saturación sin déficit.
- 🟢 Verde `·` — sin tensión.

Columnas adicionales: Línea, Modelo/familia, Equipo/modelo (si existe), DEF sem. (semanas en déficit), Sat. máx %, Déficit tot. h, Nota de situación.

**Nota:** el color refleja la tensión de la línea completa, no culpa exclusiva del proyecto.

**Bloque 7 — Qué se rompe — por semana y línea**

Tabla de conflictos: una fila por par semana/línea con déficit. Columnas: Semana, Línea, Déficit h, Carga h, Capacidad h, Saturación %, Proyectos implicados, y si el Excel tiene datos de modelo/equipo: Modelos implicados, Equipos implicados.

**Proyectos implicados** significa que esos proyectos tienen carga en esa línea y semana. No significa que sean los únicos ni los exclusivos causantes del déficit: la decisión sobre qué mover es del planificador.

**Bloque 8 — Detalle técnico / Auditoría**

Panel de botones en la columna derecha (junto a "Qué se rompe"). Cada botón abre una sección técnica:

| Botón | Contenido |
|-------|-----------|
| Proyectos excluidos | Proyectos sin línea resuelta y proyectos no calculables |
| Capacidad por línea | Tabla de capacidad h/sem por línea del escenario activo |
| Carga calculada | Tabla completa de carga por semana, línea y proyecto |
| Alternativas descartadas | Proyectos evaluados en alternativas que fueron descartados y motivo |
| Avisos | Avisos de importación del Excel y avisos del cálculo |
| Conflictos completos | Tabla completa de conflictos sin filtrar |

#### 3.7.5 Lógica de cálculo explicada sin jerga

**Paso 1 — Leer el Excel y resolver la línea**

Para cada proyecto, el sistema busca qué línea le corresponde. El orden de resolución es:
1. Si tiene `Línea preferente` y esa línea está en el escenario activo → se usa.
2. Si la línea preferente no está en el escenario, se intenta resolver con las `Líneas alternativas` declaradas, tomando la primera disponible.
3. Si no hay línea válida → el proyecto va a "Proyectos sin línea" (excluido del cálculo de carga).

**Paso 2 — Calcular la duración activa**

Si `Duración semanas` está en el Excel, se usa ese valor. Si no, se calcula:

```
duración = Semana entrega objetivo − Semana inicio mínima + 1
```

El horizonte máximo es la semana 52. Si el proyecto excede la semana 52, se recorta y se genera un aviso.

**Paso 3 — Reparto uniforme V1**

Las `Horas totales` del proyecto se distribuyen linealmente entre todas las semanas activas:

```
horas_por_semana = Horas totales / duración_usada
```

Cada semana entre `Semana inicio mínima` y `Semana inicio + duración − 1` recibe esa misma cantidad de horas. Es el **Reparto uniforme V1**: simple, sin optimización de secuencia ni picos.

**Paso 4 — Agregación por semana y línea**

Se suman las horas de todos los proyectos que coinciden en la misma semana y línea:

```
carga_semana_línea = Σ horas_por_semana de todos los proyectos en esa (semana, línea)
```

**Paso 5 — Comparar contra capacidad**

La capacidad h/sem de cada línea viene del escenario activo (mismo cálculo que Resultados, con overrides por línea si están configurados).

```
déficit_h = max(0, carga_semana_línea − capacidad_h_sem_línea)
```

Si hay déficit, se registra la semana, la línea, el déficit y los proyectos implicados.

**Paso 6 — Alternativas candidatas**

Para cada proyecto en conflicto, se evalúan sus `Líneas alternativas`. Para cada alternativa válida:
1. Se simula mover toda la carga del proyecto a esa línea alternativa.
2. Se recalcula el déficit global.
3. Si el déficit mejora (baja) → candidata. Si no mejora → descartada con motivo.

Esta evaluación es individual por proyecto (no combina movimientos de varios proyectos). En segunda ronda, el planificador sí puede aplicar acciones sobre proyectos distintos en la misma sesión.

#### 3.7.6 Cómo interpretar resultados

**"El plan cabe"** (veredicto verde): todas las líneas, en todas las semanas, tienen carga ≤ capacidad. No hay déficit. Los proyectos excluidos (si los hay) siguen siendo una advertencia a gestionar aparte.

**"Se detectan conflictos"** (veredicto rojo): al menos una línea supera su capacidad en al menos una semana. El déficit no significa que la planta no pueda producir, sino que con el plan actual y la capacidad declarada, hay semanas en que la demanda de horas supera las horas disponibles.

**Semanas con conflicto:** no todas las semanas del año están en conflicto. La tabla "Qué se rompe" muestra exactamente cuáles.

**Línea más tensionada:** la que acumula más déficit total. Puede no ser la que tiene el pico más alto en una semana concreta.

**Déficit h:** horas que faltan para ejecutar el plan tal como está definido. No es una magnitud de retraso, es una magnitud de capacidad.

**Proyectos implicados no significa culpables únicos:** si tres proyectos tienen carga en la línea L01 la semana 22, los tres aparecen como "implicados" aunque solo uno sea el detonante que supera el límite. El análisis de qué mover requiere juicio del planificador.

**Gantt rojo/naranja/verde:** el color refleja el estado de la línea en esa semana, no del proyecto en particular. Un proyecto en verde puede estar en una línea sin tensión aunque el proyecto en sí sea grande.

**Alternativas candidatas:** son simulaciones individuales. Una candidata marcada como "Libera" significa que, si ese proyecto se moviera a esa línea, el déficit desaparecería para ese proyecto. Pero pueden existir efectos secundarios en la línea destino (anotados como avisos). La decisión la toma el planificador, no la herramienta.

#### 3.7.7 Qué hay en auditoría

El panel de auditoría es para análisis técnico. No es necesario revisarlo en el uso normal. Es útil cuando:
- Hay proyectos excluidos que no se entiende por qué.
- Se quiere confirmar que la capacidad del escenario es la esperada.
- Se quiere ver la carga completa calculada semana a semana.
- Se quiere entender por qué una alternativa fue descartada.
- Hay avisos de importación que no quedaron claros.

| Sección | Cuándo revisarla |
|---------|-----------------|
| **Proyectos excluidos** | Cuando el KPI "Excluidos" > 0 y no se sabe por qué |
| **Capacidad por línea** | Para verificar que el escenario activo tiene la capacidad esperada |
| **Carga calculada** | Para confirmar el reparto semana/línea/proyecto en detalle |
| **Alternativas descartadas** | Para entender por qué una alternativa no fue considerada candidata |
| **Avisos** | Para revisar alertas de importación del Excel y del cálculo |
| **Conflictos completos** | Para ver todos los conflictos sin el filtro de la vista principal |

#### 3.7.8 Limitaciones actuales

**L10. Reparto uniforme V1 — sin optimización de secuencia**
Las horas se distribuyen linealmente entre semanas. No hay picos, no hay aceleración, no hay secuenciación inteligente. Si en la realidad un proyecto tiene más carga al inicio, eso no se captura.

**L11. No calcula estado de materiales**
El campo `Estado materiales` genera un aviso si no es OK, pero el cálculo se realiza igualmente. El módulo no valida si los materiales están disponibles ni si su estado afecta al plan.

**L12. El evaluador de alternativas candidatas es individual**
El botón "Calcular alternativas candidatas" analiza mover un proyecto a la vez. No combina movimientos de varios proyectos para buscar una solución conjunta. En cambio, en la segunda ronda sí se pueden aplicar acciones sobre proyectos distintos en la misma sesión de simulación (commit `0d286768`).

**L13. Las alternativas no se aplican automáticamente**
El módulo propone, el planificador confirma mediante botón explícito. La acción aplicada actualiza la Simulación activa (no el Excel original). El Plan real nunca se modifica.

**L14. Depende de la calidad del Excel**
Si `Semana inicio mínima` o `Horas totales` están vacías o mal formateadas, el proyecto queda excluido. Si la `Línea preferente` no coincide exactamente con los IDs del escenario, el proyecto queda sin línea.

**L15. Depende del escenario activo**
Si el escenario activo no refleja la realidad operativa (overrides desactualizados, líneas sin modelo), la capacidad calculada puede ser incorrecta o incompleta.

**L16. Horizonte máximo: semana 52**
El cálculo no supera la semana 52. Proyectos que exceden ese horizonte se recortan con aviso.

**L17. Sin autenticación específica del módulo**
Igual que el resto de la app: cualquier usuario con acceso a la URL puede cargar un Excel y calcular. No hay control de acceso por módulo.

**L18. Programación real — Exportación de simulación pendiente**
La Simulación activa no se puede exportar todavía a Excel. La funcionalidad de exportación está prevista pero no implementada. El planificador puede revisar la simulación en pantalla pero no puede generar un documento compartible con el plan simulado y las acciones aplicadas.

**L19. Programación real — Segunda ronda operativa desde junio 2026**
La tercera solapa "2ª ronda / Ajustar pendientes" está operativa. Permite aplicar acciones de ampliar semanas y mover exceso (Paralelo/Secuencial) sobre proyectos con conflictos vivos. Se pueden combinar acciones sobre proyectos distintos en la misma sesión. El modo Secuencial coloca el residual después del tramo principal para todos los tipos de proyecto (commit `0e1db08f`, junio 2026).

#### 3.7.9 Ejemplo mínimo end-to-end

**Escenario de referencia:** planta ORTUELLA, escenario activo con 4 líneas (L01–L04), capacidad ≈ 40 h/sem por línea.

---

**Ejemplo 1 — Proyecto que cabe**

Excel con:
- Proyecto: `PRY-001`
- Semana inicio mínima: `10`, Semana entrega objetivo: `14`, Duración semanas: `5`
- Horas totales: `100`, Línea preferente: `L01`

Cálculo: 100 h / 5 semanas = **20 h/sem** en L01 durante semanas 10–14.

Con capacidad = 40 h/sem en L01, la carga (20 h) no supera la capacidad. Resultado esperado: ✅ veredicto verde, sin conflictos.

---

**Ejemplo 2 — Proyecto que rompe una semana**

Añadir al Excel anterior:
- Proyecto: `PRY-002`
- Semana inicio mínima: `12`, Semana entrega objetivo: `14`, Duración semanas: `3`
- Horas totales: `90`, Línea preferente: `L01`

Cálculo: 90 h / 3 semanas = **30 h/sem** en L01 durante semanas 12–14.

Semanas 12–14: PRY-001 aporta 20 h + PRY-002 aporta 30 h = **50 h/sem** en L01.
Capacidad L01 = 40 h/sem → déficit = 10 h/sem × 3 semanas = **30 h de déficit**.

Resultado esperado: 🔴 veredicto rojo, 3 semanas con conflicto, línea más tensionada L01.

---

**Ejemplo 3 — Proyecto con línea alternativa candidata**

Modificar PRY-002:
- Línea preferente: `L01`
- Líneas alternativas: `L02`

Si L02 tiene capacidad disponible en semanas 12–14, al pulsar "Calcular alternativas candidatas", el sistema simulará mover PRY-002 a L02. Si el déficit en L01 desaparece → resultado `Libera`, candidata propuesta.

---

**Ejemplo 4 — Proyecto excluido por falta de línea**

- Proyecto: `PRY-003`
- Línea preferente: `L99` (línea que no existe en el escenario activo)
- Sin líneas alternativas declaradas

Resultado esperado: PRY-003 aparece en "Proyectos excluidos → sin línea resuelta". No contribuye al cálculo de carga.

#### 3.7.10 Acciones simulables y Simulación activa

> **Documentación detallada:** la descripción completa de los modos Paralelo/Secuencial, regla de exclusividad de línea, tipos de proyecto y clasificación de alternativas está en **`DOC_BASE_MANUAL_USUARIO Programacion Real.md`**.

El módulo incluye un sistema de simulación que permite explorar cambios sin alterar el Excel original.

**Principio fundamental:** el Plan real nunca se modifica. Toda acción genera o actualiza una **Simulación activa** (foto de trabajo acumulativa). Para descartar todos los cambios: botón **"Reiniciar simulación"**.

**Tres solapas de acción:**

| Solapa | Qué permite |
|---|---|
| **1 — Mover línea** | Mover el proyecto completo a una o varias líneas destino (carga total, reparto proporcional). |
| **2 — Ampliar semanas** | Distribuir la carga en más semanas para reducir la carga semanal. |
| **3 — Segunda ronda** | Actuar sobre conflictos que siguen vivos: ampliar semanas, mover exceso (Paralelo o Secuencial) o no actuar. Se pueden aplicar acciones sobre proyectos distintos en la misma sesión. |

**Estado junio 2026 (v0.5):** primera y segunda ronda operativas en staging. Exportación a Excel pendiente de implementación.

---

## 4. FLUJO DE USO

### 4.1 Flujo estándar del planificador (uso semanal)

```
1. Acceder a la app → sidebar muestra la última planta usada
2. [Sidebar] Seleccionar planta de trabajo
3. [Sidebar] Verificar / ajustar parámetros de planificación
   → Ver "Horas efectivas planta" actualizado en tiempo real
4. [Sidebar] Si hay cambios → "Guardar parámetros de esta planta"
5. [Tab Planificación] Seleccionar o cargar escenario activo
6. [Tab Planificación] Para cada nave/línea:
   - Seleccionar modelo (y variante LV/MV si es D&A)
   - Introducir demanda en UDS/SEM
7. [Tab Resultados] Revisar panel ejecutivo (líneas con déficit, saturación máxima, cuello)
8. [Tab Resultados] Revisar tabla resumen → detectar líneas en rojo (≥100%)
9. [Tab Resultados] Expandir detalle fino de líneas problemáticas
10. [Tab Resultados] Si es planta D&A → revisar análisis de bancos
11. Tomar decisiones: ajustar overrides por línea, reducir demanda, añadir turno
12. [Tab Planificación] Guardar cambios en escenario o guardar como nuevo escenario
```

### 4.2 Flujo de simulación anual (planificación anticipada)

```
1. [Tab Planificación] Asegurarse de tener el escenario correcto activo
2. [Tab Simulación anual] Revisar la capacidad base de planta calculada
3. [Tab Simulación anual] Descargar la plantilla Excel
4. Rellenar la plantilla con:
   - Horas de demanda previstas por modelo y semana (DEMANDA_HORAS)
   - Plan de producción comprometido si difiere de la demanda (PLAN_HORAS)
   - Semanas con capacidad reducida o paradas planificadas (SEMANAS_ESPECIALES)
5. [Tab Simulación anual] Subir el Excel rellenado
6. Revisar los avisos de validación
7. Pulsar "Calcular simulación anual"
8. Leer los 5 KPIs ejecutivos
9. Analizar el gráfico → identificar semanas de tensión, déficit y paradas
10. Revisar la tabla semanal para el detalle semana a semana
11. Si hay déficit relevante → volver a Planificación, ajustar escenario, recalcular
```

### 4.3 Flujo de análisis estratégico (esporádico, dirección)

```
1. [Tab Global] Seleccionar escenario (Máx/Prom/Mín) y turno de simulación
2. Revisar tabla Resumen Global → comparar plantas
3. Revisar gráfico "Capacidad vs Disponibilidad" → identificar plantas tensionadas
4. Usar selector de modelo → ver qué plantas pueden fabricar un modelo específico
5. [Tab Capacidad según mix] Ver rango estructural global y por línea
6. Usar Simulador (Nivel 3) → explorar cuánto podría ocupar cada modelo
7. [Tab Simulación anual] Ejecutar simulación con horizonte anual → lectura de riesgo
8. Si se detectan mejoras necesarias → registrar en "Modificaciones Necesarias" del Tab Global
```

### 4.5 Flujo de Programación real (planificador / producción)

**Parte A — Plan real y detección de conflictos**

```
1.  [Sidebar] Seleccionar planta de trabajo
2.  [Tab Planificación] Cargar o verificar el escenario activo correcto
      → Confirmar que las líneas tienen modelo asignado
      → Si hay overrides por línea relevantes, verificarlos en Resultados
3.  [Tab Programación real] Revisar el bloque de contexto:
      → Escenario activo, planta, nº de líneas y capacidad total
      → Si no cuadra con lo esperado, volver a Planificación
4.  [Tab Programación real] Descargar la Plantilla Excel con el botón "⬇️ Plantilla Excel"
5.  Rellenar el Excel con los proyectos:
      → Una fila por proyecto
      → Completar obligatorias: Proyecto, Modelo/familia, Cantidad,
        Semana inicio mínima, Semana entrega objetivo, Horas totales, Prioridad
      → Añadir Línea preferente y Líneas alternativas si se dispone de esa información
      → Guardar como .xlsx
6.  [Tab Programación real] Subir el Excel con el uploader
7.  Revisar el estado de validación:
      → "✓ N proyectos" → se puede calcular
      → Si hay avisos, leerlos (columnas opcionales añadidas con valores por defecto)
      → Si hay errores (rojo), corregir el Excel y volver a subir
8.  Pulsar "Calcular programación real"
9.  Leer el veredicto ejecutivo (verde / rojo / ámbar)
10. Si hay conflictos → revisar el Gantt (qué proyectos, qué semanas, qué líneas)
11. Revisar "Qué se rompe" → tabla semana/línea con déficit y proyectos implicados
```

**Parte B — Calcular y aplicar alternativas (Simulación activa)**

```
12. Si hay conflictos → pulsar "Calcular alternativas candidatas"
      → Revisar candidatas propuestas (Libera / Reduce)
      → Revisar avisos de cada candidata (posibles nuevos conflictos en línea destino)
13. [Acciones simulables / Mover línea]
      → Seleccionar el proyecto a mover
      → Marcar la candidata (una o varias líneas destino)
      → Si se marcan varias líneas: el sistema aplica reparto proporcional automático
      → Pulsar "Aplicar" → se crea o actualiza la Simulación activa
      → Verificar el Gantt y el estado de conflictos sobre la simulación
14. [Acciones simulables / Ampliar semanas]
      → Seleccionar el proyecto y revisar la propuesta de ampliación
      → Verificar si el nuevo fin simulado supera la entrega objetivo
      → Si conviene → pulsar "Aplicar" → se actualiza la Simulación activa
15. Repetir pasos 13–14 para cada conflicto relevante (primera ronda)
16. [Acciones simulables / 2ª ronda / Ajustar pendientes]
      → Revisar qué conflictos siguen vivos tras las acciones aplicadas
      → Verificar qué proyecto tiene aún déficit y en qué línea
      → Usar esta solapa para decidir si hay que ampliar semanas o mover nuevamente
      → (La aplicación real de segunda ronda estará disponible en el siguiente hito)
```

**Parte C — Descartar simulación si es necesario**

```
17. Si las acciones no convencen → pulsar "Descartar simulación"
      → La Simulación activa se elimina
      → Se recupera el Plan real sin cambios
      → Se puede empezar de nuevo desde el paso 12
```

**Auditoría (cuando sea necesario)**

```
18. Revisar auditoría solo si hace falta:
      → "Proyectos excluidos" si el KPI Excluidos > 0
      → "Avisos" si hay alertas que no quedaron claras
      → "Capacidad por línea" para verificar la base del cálculo
```

### 4.4 Flujo de mantenimiento de datos maestros (power user)

```
1. [Tab Configuración] → sección correspondiente:
   A. Nuevo modelo o cambio activo/inactivo → "Gestión de modelos"
   B. Nuevos tiempos de proceso → "Tiempos por modelo y proceso"
   C. Cambio físico de estaciones u operarios → "Estaciones y operarios"
   D. Nueva compatibilidad → "Compatibilidad modelo ↔ línea"
   E. Cambio en bancos disponibles → "Bancos de prueba"
   F. Cambio en asignación D&A → "Asignación valor D&A → tipo de banco"
2. Editar en la tabla (st.data_editor) con filtros si es necesario
3. Pulsar "💾 Guardar" de la sección editada
4. Verificar en Tab Resultados que los cálculos son correctos
```

---

## 5. MODELO FUNCIONAL DE DATOS

### 5.1 Entidades principales

```
PLANT
├── plant_id (PK)
├── parameters: hours_week, shifts, availability, efficiency, days_year, days_week
│
├── MODELS
│   ├── model (código)
│   ├── description
│   ├── active (bool)
│   └── plant_id
│
├── LINES_PROCESS_STATIONS
│   ├── line, nave, line_id (nave + "-" + line)
│   ├── process
│   ├── stations (decimal)
│   ├── operators_per_station (decimal, mín. efectivo: 1.0)
│   └── plant_id
│
├── MODELS_PROCESS_TIMES
│   ├── model, process
│   ├── cycle_time (legacy HH/ud — solo para conversión a horas)
│   ├── machine_time (HH/ud — tiempo fijo automático)
│   ├── labor_time (HH/ud — horas-hombre secuenciales)
│   └── plant_id
│
├── COMPATIBILITY
│   ├── nave, line, model
│   ├── compatible (0/1)
│   └── plant_id
│
├── SCENARIOS
│   ├── id, name, is_active
│   ├── line_model, line_demand, line_bench_variant (por línea)
│   └── plant_id
│
├── SCENARIO_LINE_OVERRIDES
│   ├── scenario_id, line_id
│   ├── enabled, shifts, availability, efficiency
│   └── (proc_shift_override: por proceso)
│
├── DA_BENCH_TYPE
│   ├── da_value (SL, SD, LL, LD, XD, XL)
│   ├── da_variant (LV, MV, o vacío para regla general)
│   ├── bench_type (LV, MV, XL_MV)
│   └── plant_id
│
└── BENCH_CONFIG
    ├── bench_type
    ├── qty (cantidad de bancos)
    └── plant_id
```

### 5.2 Relaciones clave

- Una **línea** tiene N **procesos** (lines_process_stations)
- Un **modelo** tiene tiempos para N **procesos** (models_process_times)
- La capacidad de una línea para un modelo = JOIN línea↔procesos × modelo↔tiempos, cruzando por `process`
- La **compatibilidad** define qué modelos pueden aparecer en el dropdown de una línea
- Un **escenario** guarda la planificación completa (qué modelo, qué demanda, qué variante D&A por línea) y los overrides de parámetros por línea

### 5.3 Persistencia

- **Primaria:** PostgreSQL (Neon). Los botones "💾 Guardar" sobreescriben la tabla completa de la planta.
- **Fallback:** CSV en `./data/` — solo lectura, no se actualizan desde la app.
- **Session state:** Planificación en curso, escenario activo, resultado de simulación anual y overrides viven en memoria de sesión. El escenario activo seleccionado persiste entre tabs gracias a una clave no-widget de session_state.

---

## 6. LÓGICA DE FUNCIONAMIENTO

### 6.1 Cálculo de horas efectivas

```
horas_efectivas = horas_semana × turnos × disponibilidad × eficiencia
semanas_equivalentes = dias_abiertos_año / dias_abiertos_semana
```

Cuando hay **overrides por línea** activos (desde el panel de Resultados), cada línea puede usar sus propios valores de turnos, disponibilidad y eficiencia, independientemente de los parámetros globales del sidebar.

### 6.2 Cálculo de capacidad por proceso

```
labor_per_operator = labor_time / operators_per_station
cycle_time_real = max(machine_time, labor_per_operator)

if cycle_time_real > 0 and stations > 0:
    capacity = (horas_efectivas × stations) / cycle_time_real
else:
    capacity = 0
```

`cycle_time_real` refleja el límite real: o bien la máquina (si es más lenta que los operarios), o bien los operarios (si son el cuello). Multiplicar por `stations` porque trabajan en paralelo.

### 6.3 Cuello de botella

```
bottleneck = proceso con menor capacity (cycle_time_real > 0 AND stations > 0)
capacity_linea = capacity_del_proceso_bottleneck
```

### 6.4 Saturación y déficit (nivel línea)

```
saturacion = (demanda / capacity_linea) × 100  [%]
deficit = max(0, demanda - capacity_linea)       [uds/sem]
```

### 6.5 Conversión a horas

```
cycle_time_total_modelo = sum(cycle_time[proceso] para todos los procesos del modelo)
  → cycle_time legacy en HH/ud

horas_demanda_sem = demanda_sem × cycle_time_total_modelo
horas_capacidad_sem = capacity_sem × cycle_time_total_modelo
```

El `cycle_time` legacy se usa **exclusivamente** para la conversión a horas (columnas h/SEM y h/AÑO). La capacidad real se calcula con `machine_time` y `labor_time`.

### 6.6 Rango estructural (Tab Capacidad según mix)

Para cada línea se calcula la capacidad con todos sus modelos compatibles activos y se obtiene máximo, promedio y mínimo. Los rangos de planta son sumas de rangos por línea.

**Nota:** No es el mix óptimo global; es la suma de los máximos independientes por línea. En la práctica, dos líneas que comparten el mismo modelo no pueden alcanzar simultáneamente su máximo individual con ese modelo.

### 6.7 Simulación anual — lógica de cálculo

La capacidad base de planta para la simulación (`cap_base_planta`) se calcula aplicando la misma lógica de overrides que Resultados: para cada línea planificada, se resuelven los parámetros efectivos (con override si está activo, globales si no) y se calcula su contribución real a la capacidad de horas. Esto garantiza coherencia entre la lectura semanal de Resultados y la lectura anual de Simulación.

SEMANAS_ESPECIALES ajusta solo la capacidad disponible de la semana indicada. No modifica el escenario, los modelos ni los parámetros globales.

### 6.8 Programación real — lógica de cálculo

El módulo aplica tres operaciones en cadena sobre los datos del Excel:

**Resolución de línea:**
```
Si Línea preferente ∈ líneas del escenario → línea asignada = Línea preferente
Si no → buscar primera Línea alternativa válida en el escenario
Si no → proyecto excluido ("sin línea")
```

**Duración usada:**
```
Si "Duración semanas" presente en Excel → dur_usada = min(Duración semanas, 52 − Semana inicio + 1)
Si no → dur_usada = Semana entrega objetivo − Semana inicio mínima + 1
dur_usada se recorta a horizonte máximo semana 52
```

**Reparto uniforme V1 (horas por semana):**
```
horas_semana_proyecto = Horas totales / dur_usada
```
Las mismas `horas_semana_proyecto` se asignan a cada semana en el rango `[Semana inicio mínima, Semana inicio + dur_usada − 1]`.

**Agregación de carga por semana y línea:**
```
carga_semana_línea = Σ horas_semana_proyecto
                     para todos los proyectos asignados a (semana, línea)
```

**Detección de déficit:**
```
déficit_h = max(0, carga_semana_línea − capacidad_h_sem_línea)
```
Donde `capacidad_h_sem_línea` es la capacidad del escenario activo para esa línea, calculada con la misma lógica de overrides que el módulo Resultados.

**Saturación de línea:**
```
saturación_% = (carga_semana_línea / capacidad_h_sem_línea) × 100
```

**Alternativas candidatas (simulación individual):**
```
Para cada proyecto P en conflicto:
  Para cada línea alternativa LA declarada para P:
    simular: mover toda la carga de P desde su línea actual a LA
    calcular déficit_global_simulado
    si déficit_global_simulado < déficit_global_base → candidata (Libera o Reduce)
    si no → descartada con motivo
```

---

## 7. LIMITACIONES Y ADVERTENCIAS

### 7.1 Limitaciones técnicas conocidas

**L1. Session state — planificación en curso no persistente entre sesiones de navegador**
Los valores de modelo y demanda por línea viven en memoria de sesión. Si el usuario cierra el navegador sin guardar el escenario, se pierde la planificación en curso. La solución es usar el gestor de escenarios para guardar antes de cerrar.

**L2. Sobreescritura total al guardar en Configuración**
Cada botón "💾 Guardar" en Configuración sobreescribe TODA la tabla de la planta en BD. No hay historial de cambios. Un error al editar y guardar puede destruir datos previos.

**L3. Modificaciones del Global no se conectan al motor**
El panel "Modificaciones Necesarias" registra hitos de mejora como anotaciones informativas. No alimentan el cálculo de capacidad.

**L4. Campo cycle_time legacy**
Coexisten dos sistemas de tiempos. Si `machine_time = 0` y `labor_time = 0` pero `cycle_time > 0`, la capacidad real calculada será 0 (ese proceso no limita) pero aparecerá en los cálculos de horas mediante `cycle_time`. Puede generar inconsistencias si no se mantiene coherencia entre ambos sistemas.

**L5. Inner join en cálculo de capacidad**
Si un modelo no tiene tiempos definidos para un proceso de la línea, ese proceso no entra en el cálculo. La capacidad puede ser optimista si faltan datos de tiempos.

**L6. Rango estructural no es mix óptimo real**
La suma de máximos por línea no representa el mix óptimo global de la planta.

**L7. Sin autenticación**
La app no tiene sistema de login. Cualquier usuario con acceso a la URL puede modificar datos en Configuración.

**L8. Análisis de bancos — informativo**
El bloque de análisis de bancos de prueba en Resultados no modifica la capacidad oficial del motor ni el cuello de botella reportado. Es una capa adicional de información, no una restricción operativa integrada.

**L9. Simulación anual — datos externos no validados contra la planificación**
La simulación anual opera con los datos introducidos en el Excel externo. No hay validación cruzada automática entre los modelos del Excel y los modelos del escenario activo. Es responsabilidad del planificador asegurar coherencia.

**L10. Programación real — Reparto uniforme V1 sin optimización de secuencia**
Las `Horas totales` de cada proyecto se distribuyen linealmente entre sus semanas activas. No hay variación por fase del proyecto, no hay aceleración ni deceleración. Si la carga real tiene picos, el modelo los aplana artificialmente.

**L11. Programación real — No calcula estado de materiales**
El campo `Estado materiales` solo genera un aviso informativo. El cálculo no bloquea proyectos con materiales no disponibles.

**L12. Programación real — Evaluación inicial individual de alternativas**
El análisis de alternativas evalúa un proyecto a la vez. No busca combinaciones de movimientos de varios proyectos que podrían resolver el déficit de forma conjunta.

**L13. Programación real — Alternativas candidatas: aplicación manual o vía Simulación activa**
Las candidatas son propuestas. El planificador puede aplicarlas directamente desde las solapas "Mover línea" y "Ampliar semanas" generando una Simulación activa. La vía recomendada dentro de la app es trabajar con Simulación activa. Cualquier cambio externo del Excel queda fuera del flujo de simulación de la app.

**L14. Programación real — Depende de la calidad del Excel**
Proyectos con `Horas totales < 1`, `Semana inicio mínima` fuera de 1–52, o duración calculada ≤ 0 quedan excluidos como "no calculables". El sistema lo indica en auditoría.

**L15. Programación real — Línea preferente debe coincidir exactamente con IDs del escenario**
Si hay discrepancias de mayúsculas, espacios o guiones entre el Excel y los IDs del escenario, la línea no se resuelve y el proyecto queda excluido.

**L16. Programación real — Horizonte máximo semana 52**
El cálculo no proyecta más allá de la semana 52. Proyectos que se extienden más allá son recortados con aviso.

### 7.2 Preguntas abiertas para el manual definitivo

**D1.** ¿Cuál es la frecuencia esperada de actualización de los parámetros de sidebar? ¿Semanal? ¿Solo cuando cambia la realidad operativa?

**D2.** ¿El campo "Disponibilidad" debe incluir las paradas por mantenimiento? ¿También ausentismo? ¿Hay un criterio estándar por planta?

**D3.** ¿El proceso de aprobación para cambios en Configuración es libre o requiere validación por un responsable técnico?

**D4.** Las "Modificaciones Necesarias" del Tab Global, ¿tienen flujo de seguimiento? ¿Se exportan o se integran con algún sistema de proyectos?

**D5.** Para la simulación anual, ¿existe un criterio corporativo para definir las semanas especiales (paradas, festivos, mantenimientos)? ¿O lo gestiona cada planta de forma independiente?

**D6.** ¿El simulador de Nivel 3 (Tab 4) está pensado para presentaciones o para toma de decisiones operativas?

---

## 8. CASOS DE USO RECOMENDADOS

### CU-01: Revisión semanal de capacidad
**Quién:** Planificador de planta
**Cuándo:** Inicio de semana
**Flujo:** Sidebar → parámetros → Planificación → selección de modelos y demanda → Resultados → revisar saturación y cuellos → ajustar si necesario → guardar escenario.

### CU-02: Análisis de impacto de un cambio de mix
**Quién:** Planificador / Ingeniero
**Cuándo:** Cuando llega un pedido especial o cambia la previsión de venta
**Flujo:** Planificación → duplicar escenario activo → cambiar modelos → Resultados → comparar escenarios → decidir si el cambio es viable.

### CU-03: Planificación de capacidad anual
**Quién:** Planificador / Dirección
**Cuándo:** Cierre de plan anual, revisión trimestral
**Flujo:** Definir escenario base en Planificación → Simulación anual → rellenar plantilla con previsión de demanda 52 semanas → calcular → revisar KPIs + gráfico + tabla → identificar semanas críticas → ajustar escenario o negociar demanda.

### CU-04: Comparación estratégica de capacidad entre plantas
**Quién:** Dirección / Estrategia
**Cuándo:** Decisiones de inversión, reasignación de producción entre plantas
**Flujo:** Tab Global → escenario Promedio → tabla Resumen Global → seleccionar modelo específico → comparar plantas que pueden fabricarlo → Tab Capacidad según mix por planta → Simulación anual si se necesita horizonte temporal.

### CU-05: Alta de una nueva línea o modelo
**Quién:** Ingeniero de procesos (Power User)
**Cuándo:** Incorporación de nueva línea o modelo al sistema
**Flujo:** Configuración → Gestión de modelos (añadir y activar) → Tiempos por modelo y proceso (rellenar machine_time y labor_time) → Estaciones y operarios (definir estaciones y operarios) → Compatibilidad (marcar qué líneas pueden fabricarlo) → Planificación (verificar que aparece en el dropdown) → Resultados (verificar cálculo).

### CU-06: Revisión de programación real por proyectos

**Quién:** Planificador / Responsable de producción / Ingeniería de procesos

**Cuándo:** Cuando se quiere comprobar si la lista de proyectos comprometidos cabe en la capacidad de la planta, antes de comprometerse con los plazos de entrega o ante señales de sobrecarga operativa.

**Flujo:**
1. Tener el escenario activo correcto en Planificación (modelos asignados, overrides actualizados si procede).
2. Preparar el Excel PROGRAMACION_REAL con los proyectos del período (mínimo: Proyecto, Modelo/familia, Cantidad, Semana inicio mínima, Semana entrega objetivo, Horas totales, Prioridad).
3. Ir al Tab Programación real → verificar escenario y capacidad base → subir Excel.
4. Pulsar "Calcular programación real".
5. Leer el veredicto: si verde, el plan cabe → documentar y cerrar. Si rojo, analizar conflictos.
6. Para cada conflicto: revisar el Gantt y "Qué se rompe" → identificar semanas y líneas tensionadas → revisar proyectos implicados.
7. Calcular alternativas candidatas → evaluar si alguna mejora la situación.
8. Decidir: mover proyectos (actualizar Excel), negociar plazos, ampliar capacidad (ajustar escenario), o aceptar el riesgo con conocimiento.
9. Si se decide cambiar: actualizar Excel → subir de nuevo → recalcular → verificar que el conflicto se resuelve.

---

## 9. GLOSARIO BÁSICO

| Término | Definición |
|---------|-----------|
| **Capacidad** | Número máximo de unidades que una línea puede producir en un período, limitada por el cuello de botella |
| **Cuello de botella** | Proceso de la línea con menor capacidad; determina la velocidad máxima de toda la línea |
| **Disponibilidad** | Factor (0–1): tiempo real de producción sobre el tiempo total disponible, descontando paradas planificadas |
| **Eficiencia** | Factor (0–1): rendimiento real de la producción respecto al teórico (OEE parcial) |
| **Horas efectivas** | `horas/sem × turnos × disponibilidad × eficiencia` — horas reales de producción por semana |
| **Saturación** | Porcentaje de uso de la capacidad: demanda/capacidad × 100 |
| **Déficit** | Gap entre demanda y capacidad disponible (en unidades o en horas) |
| **Machine time** | Tiempo automático fijo por unidad, no reducible añadiendo operarios (ej: ciclo de horno, test automático) |
| **Labor time** | Horas-hombre totales necesarias por unidad, reducibles añadiendo operarios en paralelo |
| **Cycle time real** | `max(machine_time, labor_time / operarios)` — tiempo real de ciclo efectivo |
| **Nave** | Agrupación física de líneas dentro de una planta (N1, N2…) |
| **Line ID** | Identificador compuesto: `nave + "-" + línea` (ej: N1-L01) |
| **Rango estructural** | Intervalo [mínimo, máximo] de capacidad según qué mix de modelos se produzca |
| **Techo estructural** | Suma de las capacidades máximas de todas las líneas en h/sem |
| **Semanas equivalentes** | `días_año / días_semana` — factor de anualización |
| **Mix** | Combinación de modelos producidos simultáneamente en las distintas líneas |
| **Escenario** | Configuración guardada de planificación: qué modelo y qué demanda tiene cada línea, con sus overrides de parámetros |
| **Override por línea** | Parámetros específicos (turnos, disponibilidad, eficiencia) para una línea concreta, que prevalecen sobre los globales del sidebar |
| **D&A** | Diagnóstico y Análisis — familia de modelos que requieren banco de prueba específico |
| **Variante LV / MV** | Variante del banco de prueba de un equipo D&A: Baja Tensión (LV) o Media Tensión (MV) |
| **Parada** | Semana con capacidad disponible = 0 (definida en SEMANAS_ESPECIALES); se distingue del déficit operativo |
| **Simulación anual** | Cálculo semana a semana de demanda vs capacidad a lo largo de las 52 semanas, a partir de datos externos en Excel |
| **Programación real** | Módulo que carga proyectos reales desde un Excel, reparte sus horas entre semanas y detecta conflictos de capacidad por semana, línea y proyecto |
| **Proyecto implicado** | Proyecto que tiene carga en la misma línea y semana donde hay déficit. Implica presencia en el conflicto, no culpabilidad exclusiva |
| **Línea preferente** | Línea de producción donde el planificador quiere ejecutar un proyecto en primer lugar. Se declara en el Excel; debe coincidir con los IDs del escenario activo |
| **Líneas alternativas** | Líneas candidatas secundarias donde el proyecto podría ejecutarse si la preferente no está disponible o genera conflicto. Se declaran en el Excel separadas por coma |
| **Alternativa candidata** | Resultado del análisis de alternativas: una combinación proyecto + línea que, si se aplicara, reduciría o eliminaría el déficit actual. Son propuestas, no cambios automáticos |
| **Reparto uniforme V1** | Lógica de distribución de carga de la versión actual: las Horas totales del proyecto se dividen linealmente entre todas sus semanas activas, sin variación por fase ni por prioridad dentro del proyecto |
| **Qué se rompe** | Tabla del módulo Programación real que muestra las semanas y líneas donde la carga calculada supera la capacidad disponible, con el déficit en horas y los proyectos implicados |
| **Auditoría técnica** | Panel de botones del módulo Programación real que da acceso a información de detalle: proyectos excluidos, capacidad por línea, carga calculada, alternativas descartadas, avisos y conflictos completos |
| **Proyecto no calculable** | Proyecto que tiene datos de Excel inválidos (Horas totales < 1, Semana inicio fuera de 1–52, duración ≤ 0) y que por eso no puede entrar en el cálculo de carga |
| **Proyecto sin línea** | Proyecto cuya Línea preferente no existe en el escenario activo y cuyas Líneas alternativas (si las hay) tampoco coinciden. Se excluye del cálculo de carga pero aparece en auditoría |
| **Simulación activa** | Foto de trabajo generada al aplicar acciones en Programación real (mover línea, ampliar semanas). Acumula las acciones aplicadas sobre el Plan real sin modificarlo. Puede descartarse en cualquier momento para volver al Plan real intacto |
| **Plan real** | Carga calculada directamente desde el Excel PROGRAMACION_REAL, sin modificaciones. Nunca se altera directamente: los cambios simulados viven en la Simulación activa |
| **Acciones simulables** | Sección del módulo Programación real con tres solapas: Mover línea, Ampliar semanas y 2ª ronda / Ajustar pendientes. Permite explorar cambios sobre el plan sin alterar los datos originales |
| **Mover línea (Programación real)** | Acción que desplaza un proyecto completo a una o varias líneas destino. El proyecto se mueve en su totalidad; si hay varias líneas destino el reparto es proporcional automático (50/50 para dos líneas, aprox. 33/33/33 para tres). No mueve solo el exceso |
| **Ampliar semanas (Programación real)** | Acción que distribuye la carga de un proyecto en más semanas para reducir la carga semanal. Puede generar retraso respecto a la semana de entrega objetivo. La decisión la toma el planificador |
| **Segunda ronda** | Tercera solapa de Acciones simulables. Muestra los conflictos que siguen vivos después de aplicar acciones en la primera ronda. Trabaja exclusivamente sobre la Simulación activa. En construcción funcional a 25-05-2026 |
| **Reparto proporcional** | Distribución de carga de un proyecto entre varias líneas destino al moverlo. El sistema divide automáticamente el total de horas en partes iguales entre las líneas seleccionadas |

---

## 10. BASE PARA FUTURA PRESENTACIÓN END-TO-END (10–12 SLIDES)

El siguiente esquema puede servir como guión directo para construir la presentación ampliada:

| Slide | Contenido sugerido | Fuente en este documento |
|-------|-------------------|--------------------------|
| 1 | Portada: "Motor Estratégico de Capacidad Productiva" | §1.1 |
| 2 | Problema que resuelve — preguntas de negocio que responde | §1.1, §1.2 |
| 3 | Arquitectura de la solución: plantas, tabs, flujo general | §2.1, §2.3 |
| 4 | Demo: Sidebar + Planificación + escenarios | §3.2, §4.1 pasos 1–6 |
| 5 | Demo: Resultados — panel ejecutivo + tabla + overrides | §3.4, §4.1 pasos 7–11 |
| 6 | Lógica de cálculo para no técnicos: machine/labor time, bottleneck | §6.2, §6.3 |
| 7 | Capacidad según mix — rango estructural y simulador | §3.5 |
| 8 | Simulación anual — flujo de uso (planificador) | §3.6.1–3.6.5, §4.2 |
| 9 | Simulación anual — lectura de resultados: KPIs + gráfico + tabla | §3.6.6 |
| 10 | Casos de uso reales: revisión semanal, plan anual, comparación entre plantas | §8 CU-01, CU-03, CU-04 |
| 11 | Visión Global multiplanta — dirección | §3.1 |
| 12 | Limitaciones conocidas, roadmap y próximos pasos | §7 |

---

## Cambios introducidos respecto al documento base anterior (marzo 2026)

### Apartados actualizados

- **§2.2 Sidebar:** añadida la franja superior de controles de interfaz (modo oscuro + selector de idioma ES/EN/EU)
- **§2.3 Tabs:** añadido el Tab 5 — Simulación anual. Renumerado Tab 4 (Capacidad según mix) sin cambio de contenido.
- **§3.2 Planificación:** reescrito el funcionamiento del dropdown — ahora es un único selector combinado `Modelo · Variante` por línea (antes eran dos campos separados). Añadida sección completa de gestión de escenarios (guardar, cargar, duplicar, renombrar, eliminar, marcar como activo).
- **§3.3 Configuración:** añadida la sección de Bancos de prueba (bancos por tipo y asignación D&A → tipo de banco) para plantas con líneas D&A.
- **§3.4 Resultados:** añadidos el panel ejecutivo de resumen, el comparador de escenarios, los overrides por línea (turnos/disponibilidad/eficiencia individuales y por proceso), la lectura de personas equivalentes (FTE informativo) y el bloque de análisis de bancos de prueba D&A.

### Apartados añadidos

- **§3.6 — Simulación anual:** sección completamente nueva. Describe la funcionalidad de simulación de capacidad vs demanda a lo largo de 52 semanas: condiciones previas, capacidad base, plantilla descargable, validación del Excel, cálculo semanal, KPIs ejecutivos, gráfico y tabla.
- **§8 — Casos de uso recomendados:** cinco casos de uso completos con perfil, momento de uso y flujo paso a paso.
- **§10 — Base para futura presentación:** esquema de 12 slides con correspondencia explícita a secciones del documento.

### Apartados reformulados

- **§5.1 Entidades principales:** añadidas las entidades SCENARIOS, SCENARIO_LINE_OVERRIDES, DA_BENCH_TYPE y BENCH_CONFIG.
- **§6.1 Horas efectivas:** ampliado con la mención a los overrides por línea.
- **§7 Limitaciones:** añadidas L8 (análisis de bancos informativo) y L9 (simulación anual — datos externos no validados contra planificación). Actualizada L1 con la solución del gestor de escenarios. Limpiadas preguntas abiertas.
- **§Glosario:** añadidos términos: Escenario, Override por línea, D&A, Variante LV/MV, Parada, Simulación anual.

### Apartados obsoletos o absorbidos

- El apartado **"ANEXO B — Plantas y líneas reales"** se ha eliminado por obsolescencia y porque esos datos varían con frecuencia. La fuente de verdad son los datos de BD, no un anexo estático en un documento.
- La numeración de tabs se ha actualizado (el original tenía 5 tabs 0–4; ahora son 6 tabs 0–5).

### Partes especialmente relevantes para la futura presentación ampliada

- §3.6 completo (Simulación anual) — es la funcionalidad más diferencial respecto al documento anterior
- §8 Casos de uso — directamente reutilizable como estructura narrativa de la presentación
- §10 — esquema ya listo para slide a slide
- §3.4.1 Panel ejecutivo y §3.4.7 Análisis de bancos — novedades importantes de Resultados

### Qué aporta específicamente la incorporación de la simulación anual

La funcionalidad de simulación anual eleva el motor de una herramienta de **lectura semanal puntual** a una herramienta de **planificación de horizonte anual**. Permite al planificador y a la dirección responder preguntas estratégicas que antes requerían hojas de cálculo externas:

- ¿Cuántas semanas del año tenemos déficit de capacidad?
- ¿Cuándo es el pico de tensión y cuánto nos pasamos?
- ¿Cuál es el agujero acumulado anual en horas?
- ¿Qué semanas están planificadas como paradas y cuánta demanda se acumula en ellas?

La integración con el escenario activo (mismo cálculo de overrides que Resultados) garantiza que la simulación anual es coherente con la lectura semanal, no una estimación desconectada.

---

---

### Mayo 2026 — Incorporación de Programación real (Tab 6)

#### Apartados añadidos

- **§2.3 Tabs:** añadida la fila del Tab 6 — 📋 Programación real en la tabla de pestañas.
- **§3.7 TAB 6 — Programación real:** sección completamente nueva con 9 subapartados: propósito, condiciones previas, estructura del Excel (obligatorias, opcionales, aliases), flujo de uso en pantalla (8 bloques), lógica de cálculo sin jerga, interpretación de resultados, auditoría técnica, limitaciones del módulo y ejemplo mínimo end-to-end con 4 casos.
- **§4.5 Flujo de Programación real:** flujo de 13 pasos para planificador/producción.
- **§6.8 Programación real — lógica de cálculo:** fórmulas de resolución de línea, duración usada, reparto uniforme V1, agregación de carga, déficit y alternativas candidatas.
- **§7.1 Limitaciones:** añadidas L10–L16 específicas del módulo Programación real (reparto uniforme, materiales, alternativas individuales, calidad del Excel, coincidencia de IDs, horizonte semana 52).
- **§8 Casos de uso:** añadido CU-06 (Revisión de programación real por proyectos) con perfil, cuándo usarlo y flujo completo de 9 pasos.
- **§9 Glosario:** añadidos 11 términos nuevos: Programación real, Proyecto implicado, Línea preferente, Líneas alternativas, Alternativa candidata, Reparto uniforme V1, Qué se rompe, Auditoría técnica, Proyecto no calculable, Proyecto sin línea.

#### Qué aporta específicamente la incorporación de Programación real

El módulo de Programación real eleva el Motor de una herramienta de **capacidad estructural** a una herramienta de **validación de compromisos reales por proyecto**. Permite al planificador responder, antes de comprometer plazos:

- ¿El plan de proyectos comprometido cabe en la planta esta semana? ¿Y la siguiente?
- ¿Qué proyectos concretos generan tensión en qué líneas y semanas?
- ¿Hay alguna línea alternativa que alivie el conflicto sin generar uno nuevo?
- ¿Cuántos proyectos quedan fuera del cálculo por datos incompletos?

La integración con el escenario activo (misma capacidad calculada que Resultados, incluidos overrides por línea) garantiza coherencia entre la lectura de capacidad estructural y la validación del plan de proyectos real.

---

---

### Actualización 25-05-2026 — Estado de Programación real

#### Qué está operativo

- Carga de Excel PROGRAMACION_REAL con validación de columnas y aliases.
- Cálculo de programación real (reparto de carga, cruce con capacidad, detección de conflictos).
- Gantt del Plan real y de la Simulación activa.
- Cálculo de alternativas candidatas (Mover línea, Ampliar semanas).
- Aplicación de alternativas seleccionadas desde las solapas "Mover línea" y "Ampliar semanas".
- Creación y acumulación de acciones sobre la Simulación activa.
- Descartar simulación y volver al Plan real.

#### Qué está en validación

- Tercera solapa "2ª ronda / Ajustar pendientes":
  - Detección de conflictos vivos tras la primera ronda: operativa.
  - Asociación del conflicto con el proyecto real (ej. PRY-001 movido a N1-L12, con déficit pendiente en N1-L12): implementada, en validación en staging.
  - Consola visual de decisión (opciones Ampliar / Mover / No actuar por proyecto): implementada, en validación.
  - Aplicación real de ajustes de segunda ronda: pendiente de implementar (siguiente hito).

#### Qué está pendiente

- Exportación de la Simulación activa a Excel.
- Aplicación real de acciones de segunda ronda desde la tercera solapa.
- Ajustar en destino completo como flujo integrado (mover + ampliar en el mismo hito).
- Reglas de acumulación para evitar doble aplicación o mezcla de Plan real y Simulación.

#### Funciones fuera del alcance actual

No están implementadas ni planificadas a corto plazo:

- Mover solo el exceso de horas (no el proyecto completo).
- Mover un porcentaje parcial de carga.
- Reducir semanas de un proyecto.
- Optimización automática de la planificación.
- Usar la Simulación activa como nuevo Plan oficial.
- Exportación completa final (depende de cerrar lo funcional primero).

#### Advertencia

El módulo está en desarrollo activo. El estado descrito puede evolucionar en cada sprint. Consultar el archivo de plan vivo `2026-05-25_PLAN_IMPLEMENTACION_MOTOR_ESTRATEGICO_PROGRAMACION_REAL.md` para el estado actualizado de hitos y próximos pasos.

---

*Documento actualizado el 25-05-2026 a partir de análisis del código fuente real (app.py — rama staging) y contraste con el documento base de mayo 2026.*
