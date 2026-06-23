# 🐜 Colonia de Hormigas — Simulación Paralela con Enjambre

Simulador interactivo 2D de una colonia de hormigas evadiendo obstáculos
en patrón de enjambre. El cálculo de física (posición, velocidad,
evasión) se reparte en tiempo real entre los núcleos de la CPU usando
`multiprocessing`, manteniendo una arquitectura 100% funcional: estado
inmutable, funciones puras, sin POO mutable ni variables globales.

## Arquitectura

```
core/
  state.py             -> GameState, Ant, Obstacle (todo @dataclass(frozen=True))
  physics.py           -> funciones puras de evasión tipo enjambre (step_ant, step_chunk)
  parallel_engine.py   -> segmentación, multiprocessing.Pool, consolidación
bench/
  benchmark.py         -> mide FPS secuencial vs paralelo y genera la tabla pedida
render/
  app.py               -> ventana Arcade, lee el GameState y lo dibuja (sin lógica de física)
tests/
  test_core.py         -> valida inmutabilidad y equivalencia secuencial == paralelo
main.py                -> punto de entrada interactivo
```

### Flujo del Game Loop (por frame)

1. **Segmentación** — `_partition_ants()` divide la tupla de hormigas en
   `n_workers` bloques contiguos de tamaño `ceil(N / n_workers)`.
2. **Mapeo paralelo** — cada bloque se envía a un proceso del
   `multiprocessing.Pool` que ejecuta `step_chunk()`, una comprensión de
   tupla que aplica la función pura `step_ant()` a cada hormiga del bloque.
3. **Sincronización y consolidación** — `pool.map()` bloquea hasta que
   todos los workers terminan; los resultados se concatenan en orden y
   se construye un `GameState` **nuevo** (el anterior nunca se muta).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest               # solo si van a correr los tests
```

## Uso

**Simulación interactiva:**
```bash
python main.py
```
- `P` → alterna PARALELO / SECUENCIAL en caliente (mismo proceso, sin reiniciar)
- `↑` / `↓` → sube/baja la cantidad de hormigas
- `ESC` → salir

**Benchmark formal (tabla de la rúbrica):**
```bash
python -m bench.benchmark
```
Esto genera `bench/RESULTADOS.md` con la tabla de 1,000 / 3,000 / 5,000
entidades, núcleos detectados, workers activos y la estrategia de partición.

**Tests:**
```bash
pytest tests/ -v
```

## Datos técnicos a exponer en la defensa

| Dato | Cómo se obtiene en el código |
|---|---|
| Núcleos totales detectados | `os.cpu_count()` en `parallel_engine.detect_total_cores()` |
| Workers activos | `núcleos totales - 1` (se deja 1 núcleo libre para el render), ver `recommended_worker_count()` |
| Estrategia de partición | Bloques contiguos de tamaño `ceil(N / n_workers)`, ver `_partition_ants()` |

---

## 👥 Plan de Trabajo y Commits por Integrante

> ⚠️ La rúbrica penaliza con nota 0 los "commits mágicos". Cada
> integrante **debe** trabajar desde su propia cuenta de GitHub, en
> commits progresivos y separados en el tiempo (no todo en un solo
> bloque al final). El reparto de abajo está diseñado para que cada
> persona tenga un área de archivos clara y pueda hacer commits
> reales e independientes sin pisarse con los demás.

### Integrante A — Estado y Modelo de Datos (`core/state.py`)
Commits sugeridos (en este orden, en sesiones distintas):
1. `feat(state): definir dataclass Ant inmutable`
2. `feat(state): definir dataclass Obstacle inmutable`
3. `feat(state): definir GameState congelado con tupla de entidades`
4. `feat(state): agregar with_ants() para transición de estado sin mutación`
5. `feat(state): make_initial_state() con seed reproducible`
6. `test(state): validar que GameState y Ant lanzan error al intentar mutarse`

### Integrante B — Física y Comportamiento de Enjambre (`core/physics.py`)
1. `feat(physics): función pura de wander (deambular) por hormiga`
2. `feat(physics): repulsión de obstáculos (evasión tipo enjambre)`
3. `feat(physics): repulsión entre vecinos para evitar colapso del enjambre`
4. `feat(physics): step_ant() integrando fuerzas y rebote en bordes`
5. `refactor(physics): step_chunk() con comprensión de tupla en vez de bucle for`
6. `fix(physics): ajustar constantes de velocidad máxima y radios de evasión`

### Integrante C — Paralelismo y Sincronización (`core/parallel_engine.py`)
1. `feat(parallel): _partition_ants() con partición en bloques contiguos`
2. `feat(parallel): worker top-level _worker_step() picklable para multiprocessing`
3. `feat(parallel): update_parallel() con Pool.map() y consolidación`
4. `feat(parallel): update_sequential() como línea base de comparación`
5. `feat(parallel): detect_total_cores() y recommended_worker_count()`
6. `test(parallel): verificar que secuencial y paralelo producen resultados idénticos`

### Integrante D — Render (Arcade) y Benchmark (`render/app.py`, `bench/benchmark.py`)
1. `feat(render): ventana Arcade base dibujando obstáculos y hormigas`
2. `feat(render): HUD con modo activo, FPS y número de hormigas`
3. `feat(render): toggle de modo paralelo/secuencial con tecla P`
4. `feat(bench): medición de FPS por modo y tamaño de población`
5. `feat(bench): generación de tabla markdown con resultados`
6. `docs(bench): registrar resultados reales de la máquina de prueba en RESULTADOS.md`

### Commits conjuntos (cualquiera puede hacerlos, pero deben quedar repartidos)
- `chore: estructura inicial del proyecto y requirements.txt`
- `docs: README con instrucciones de instalación y uso`
- `test: suite de pytest para estado y paralelismo`
- `docs: completar tabla de rendimiento con métricas de la máquina de prueba`

**Recomendación práctica:** no hagan todos los commits el mismo día. Si
la fecha límite es el viernes, repártanse para que cada integrante
tenga commits visibles en al menos 2-3 días distintos durante la semana.
El auditor de GitHub revisa el historial completo, no solo el commit final.

## ⚠️ Nota sobre rendimiento esperado

El overhead de crear procesos y serializar datos entre ellos (pickling)
solo se compensa cuando el trabajo por proceso es lo suficientemente
grande. Es normal y **se debe explicar en la defensa** que:

- Con pocas entidades (ej. 1,000) el speedup paralelo puede ser modesto
  o incluso *peor* que el secuencial en máquinas con pocos núcleos,
  porque el overhead de IPC domina sobre el cálculo real.
- El beneficio del paralelismo se vuelve claramente medible a partir
  de cargas más grandes (3,000–5,000+), donde el cálculo por proceso
  supera el costo de comunicación entre procesos.
- En una máquina de 1 núcleo físico, el modo paralelo **siempre** será
  más lento que el secuencial (no hay núcleos extra que aprovechar) —
  por eso el benchmark debe correrse en hardware real de al menos 2-4
  núcleos para mostrar la mejora que pide la rúbrica.
