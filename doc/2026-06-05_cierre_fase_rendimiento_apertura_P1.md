# Motor Estratégico de Capacidad Productiva
## Cierre de Fase de Rendimiento · Apertura de Fase P1
**Fecha:** 5 de junio de 2026 · Rama: `staging`

---

## 1. Resumen ejecutivo

Entre las fases 0B.1 y 0C se ha completado un ciclo de optimización de rendimiento sobre el Motor Estratégico. El objetivo era reducir los tiempos de respuesta de la aplicación para que la navegación diaria sea fluida y los escenarios de planificación se gestionen sin esperas perceptibles.

Los resultados son satisfactorios: la navegación entre pantallas ya visitadas responde en menos de 1 segundo, los escenarios de planificación se leen y escriben sin retrasos apreciables, y el único tiempo largo restante —la primera carga de la aplicación— se ha analizado exhaustivamente y se concluye que es un coste inevitable de la infraestructura utilizada (servidores Render y base de datos Neon), no un problema de código.

La fase de rendimiento se da por **cerrada y congelada**. A partir de aquí el equipo se enfoca en la estabilización funcional y la experiencia de usuario para el piloto.

---

## 2. Qué se ha optimizado

Se realizaron seis intervenciones ordenadas de menor a mayor impacto:

| Fase | Descripción | Tipo |
|------|-------------|------|
| 0B.1 | Panel de medición de tiempos interno (`APP_PROFILE`) | Herramienta de diagnóstico |
| 0B.2 | Datos de configuración general cacheados durante 5 minutos | Optimización de caché |
| 0B.3 | Medición del cálculo de capacidad de líneas (Programación real) | Herramienta de diagnóstico |
| 0B.4 | Lista de escenarios cacheada, con invalidación validada | Optimización de caché |
| 0B.5 | Escenario activo cacheado, con invalidación validada | Optimización de caché |
| 0C | Análisis de carga fría y cierre como coste de infraestructura | Análisis — sin cambio de código |

Todas las cachés incluyen lógica de invalidación: cuando el usuario activa, guarda, renombra, duplica o elimina un escenario, los datos obsoletos se descartan y la siguiente lectura va directamente a base de datos.

---

## 3. Qué métricas han mejorado

### Antes de las optimizaciones (referencia)
- Cada cambio de pantalla forzaba 2–3 consultas a base de datos.
- Cambiar de planta relanzaba todas las consultas incluso si la planta ya había sido visitada.
- Cada carga de la lista de escenarios abría una conexión nueva a Neon (~1 segundo).
- El escenario activo se recargaba en cada rerun sin necesidad.

### Después

| Métrica | Antes | Después |
|---------|-------|---------|
| Navegación caliente (pantalla ya visitada) | ~2–3 s | ~1 s |
| Cambio a planta ya visitada | ~2–3 s | ~617–882 ms |
| Carga de lista de escenarios (caliente) | ~1.030 ms | ~0.2 ms |
| Carga de escenario activo (caliente) | ~1.188 ms | ~0.3 ms |
| Datos de configuración de planta (caliente) | ~1.000 ms | ~0.4–0.8 ms |
| Programación real con cálculo completo | sin cambio | ~2–4 s (esperado) |
| Primera carga (frío) | ~10–18 s | ~10–18 s (sin cambio, aceptado) |

El cálculo de capacidad por línea en Programación real (~800–900 ms) se ha medido y documentado. No se ha tocado porque es un cálculo necesario que no tiene opciones de optimización seguras sin riesgo funcional.

---

## 4. Qué queda pendiente y por qué no se toca ahora

### Carga fría inicial (~10–18 segundos)

La aplicación tarda entre 10 y 18 segundos en responder la primera vez que un usuario la abre, o cuando lleva mucho tiempo sin usarse.

**Causa:** El servidor de Render "duerme" cuando no recibe tráfico. Neon (la base de datos) también parte de estado inactivo. Arrancar ambos servicios requiere abrir 5 conexiones de red independientes de forma secuencial, cada una con su propio coste de establecimiento (~500–1000 ms por conexión).

**Por qué no se toca:** No es un problema de código. Cualquier reducción significativa requeriría o bien contratar un plan de infraestructura que no duerma, o bien una reestructuración profunda del código que introduce riesgo sobre funcionalidades ya validadas. El equipo ha decidido aceptar este coste como parte del modelo de despliegue actual del piloto.

### Cálculo de Programación real (~800–900 ms por ejecución)

Es un cálculo intensivo que recorre todas las líneas planificadas. No tiene caché porque sus entradas cambian con cada interacción del usuario.

**Por qué no se toca:** El tiempo es aceptable para la operativa del piloto. Optimizarlo requeriría modificar la lógica de cálculo, lo cual está fuera del alcance de esta fase.

---

## 5. Qué queda prohibido tocar salvo aprobación expresa

Las siguientes áreas están **congeladas para cambios de rendimiento** hasta nueva instrucción:

- Lógica de cálculo de capacidad (Programación real, Resultados, Simulación anual, Gantt, Alternativas).
- Funciones de caché y sus puntos de invalidación: `load_active_scenario`, `list_scenarios`, `load_plant_data`, `load_table`.
- `session_state` funcional (estructuras de datos de planificación por planta y escenario).
- Motor de cálculo (`engine.py`).
- Parser de Excel.
- Rama `main` / productivo — ningún cambio sin proceso de validación completo.

Cualquier cambio en estas áreas requiere análisis previo, aprobación explícita y validación en `staging` antes de merge.

---

## 6. Decisión de congelación de rendimiento

> **La fase de rendimiento queda cerrada.**
>
> El código ha alcanzado el límite de lo optimizable sin riesgo funcional dado el modelo de infraestructura actual. Las métricas de navegación caliente son satisfactorias para el piloto. No se abrirán nuevas microfases de rendimiento salvo que aparezca una regresión medida con `APP_PROFILE`.
>
> El panel de profiling (`APP_PROFILE=1`) permanece disponible para diagnóstico puntual pero no estará activo en producción.

---

## 7. Nueva fase P1: Estabilización funcional y UX del piloto

La Fase P1 tiene como propósito dejar la aplicación lista para ser usada de forma autónoma por los usuarios del piloto, sin necesidad de soporte técnico constante.

El foco cambia de rendimiento a **fiabilidad funcional** y **claridad de uso**:
- Que los flujos principales no tengan errores silenciosos ni comportamientos confusos.
- Que los usuarios entiendan qué hace cada pantalla y cómo recuperarse de un error.
- Que los datos mostrados sean siempre coherentes con lo que el usuario ha configurado.

---

## 8. Objetivos de P1

### Funcionales
- Verificar que todos los flujos de escenario (crear, activar, guardar, duplicar, eliminar) funcionan de extremo a extremo sin estados inconsistentes.
- Verificar que Resultados y Simulación anual reflejan siempre el escenario activo vigente.
- Verificar que el cambio de planta no deja datos de la planta anterior visibles.
- Verificar que los cálculos de Programación real son coherentes con los parámetros configurados.

### UX y mensajes
- Revisar que los mensajes de error y de confirmación son claros y aparecen donde el usuario los espera.
- Identificar pantallas o controles que generen confusión en uso real.
- Asegurar que los textos en los tres idiomas (es/en/eu) están completos y son correctos.

### Datos y exportación
- Verificar que las exportaciones a Excel producen ficheros válidos y con los datos esperados.
- Verificar que el parser de Excel (importación) maneja correctamente los casos de error sin romper la sesión.

### Estabilidad
- Identificar y documentar cualquier flujo que provoque error técnico visible al usuario o pantalla en blanco.
- Verificar el comportamiento con plantas sin datos configurados.
- Verificar el comportamiento cuando no hay escenario activo.

---

## 9. Checklist de validación de piloto

Este checklist debe completarse en `staging` antes de promover a `main`.

### Gestión de plantas
- [ ] Crear planta nueva — aparece en selectbox sin recargar manualmente.
- [ ] Cambiar entre plantas — los datos de la nueva planta se cargan correctamente.
- [ ] Planta sin datos configurados — la app no rompe, muestra mensaje claro.

### Parámetros de planificación
- [ ] Guardar parámetros — los valores se persisten y se recuperan al volver.
- [ ] Cambiar parámetros y navegar entre tabs — no se pierden los cambios hasta guardar.

### Escenarios
- [ ] Crear escenario nuevo — aparece en lista, no activa automáticamente.
- [ ] Activar escenario — los modelos y demandas se cargan en Planificación.
- [ ] Guardar cambios sobre escenario activo — los cambios se reflejan inmediatamente.
- [ ] Renombrar escenario — el nombre nuevo aparece en todas las pantallas.
- [ ] Duplicar escenario — la copia aparece en lista como inactiva.
- [ ] Eliminar escenario inactivo — desaparece sin afectar al activo.
- [ ] Sin escenario activo — Resultados y Simulación anual muestran estado vacío sin error.

### Planificación
- [ ] Asignar modelo y demanda a cada línea — se guarda en el escenario.
- [ ] Líneas sin modelo asignado — el cálculo las ignora correctamente.

### Resultados
- [ ] Los resultados corresponden al escenario activo vigente.
- [ ] Cambiar escenario activo — Resultados refleja el nuevo escenario en el siguiente cálculo.

### Programación real
- [ ] El cálculo completa sin error con todas las líneas planificadas.
- [ ] Los avisos de advertencia son legibles y accionables.

### Simulación anual y Gantt
- [ ] Se generan sin error con datos completos.
- [ ] Se generan sin error con datos parciales (pocas líneas).

### Exportaciones
- [ ] Exportar a Excel desde Resultados produce fichero válido.
- [ ] Exportar desde Programación real produce fichero válido.

### Internacionalización
- [ ] Todos los textos visibles en español son correctos.
- [ ] Cambiar idioma a inglés — no quedan textos en español.
- [ ] Cambiar idioma a euskera — no quedan textos en español.

### Comportamiento general
- [ ] No hay pantallas en blanco ni mensajes de error técnico visibles al usuario.
- [ ] El logo y los elementos de cabecera se muestran correctamente.
- [ ] El modo oscuro no rompe ningún componente visual.

---

## 10. Siguiente paso recomendado

**Acción inmediata:** Realizar una sesión de revisión funcional en `staging` con el usuario piloto, recorriendo el checklist anterior. El objetivo es identificar los puntos de fricción reales antes de preparar correcciones.

**Criterio de paso a main:** El checklist debe estar completo al 100% en los bloques de Gestión de plantas, Escenarios, Planificación y Resultados. Los bloques de Programación real, Simulación y Gantt deben estar al 100% o con incidencias documentadas y priorizadas.

**Recomendación de proceso:** Cada corrección identificada en P1 se implementa como un commit atómico en `staging`, se valida con el checklist parcial correspondiente, y solo entonces se promueve a `main`. No se acumulan correcciones sin validar.

---

*Documento preparado para revisión interna. No es un compromiso de entrega. Las fechas y prioridades de P1 se definen en la sesión de arranque de fase con el equipo.*
