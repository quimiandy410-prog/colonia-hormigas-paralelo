"""
hola mundo
core/parallel_engine.py
=========================
Aquí vive el "Game Loop" funcional descrito en el reto:

    1. Segmentación   -> _partition_ants()
    2. Mapeo paralelo  -> update_parallel() usando multiprocessing.Pool
    3. Sincronización y consolidación -> pool.map() bloquea hasta que
       TODOS los workers terminan; luego se concatenan los resultados
       y se construye el GameState congelado nuevo.

También se incluye update_sequential(), que ejecuta exactamente la
misma función pura (step_chunk) pero en un solo proceso, sin Pool.
Comparar update_sequential() vs update_parallel() es la base de toda
la métrica de rendimiento que pide el reto.

Persona responsable sugerida: Integrante C (Paralelismo y Sincronización).
"""

from __future__ import annotations
from typing import Tuple, List
import os
import multiprocessing as mp

from core.state import GameState, Ant, Obstacle
from core.physics import step_chunk


# ---------------------------------------------------------------------------
# 1. Segmentación
# ---------------------------------------------------------------------------
def _partition_ants(
    ants: Tuple[Ant, ...], n_workers: int
) -> List[Tuple[Ant, ...]]:
    """Divide la tupla de hormigas en `n_workers` partes lo más
    proporcionales posible (chunking contiguo por índice).

    Estrategia de partición: división contigua en bloques de tamaño
    aproximadamente igual (ceil(n / n_workers)), usando slicing de
    tupla. Es la estrategia más simple y la de menor overhead de
    serialización, porque cada worker recibe un bloque contiguo y no
    hay que reconstruir índices dispersos al consolidar.
    """
    n = len(ants)
    if n_workers <= 1 or n == 0:
        return [ants]

    chunk_size = -(-n // n_workers)  # ceil division
    return [
        ants[i : i + chunk_size]
        for i in range(0, n, chunk_size)
    ]


# ---------------------------------------------------------------------------
# Worker top-level (debe ser función de módulo, no closure/lambda, para
# que sea "picklable" y multiprocessing pueda enviarla a cada proceso hijo)
# ---------------------------------------------------------------------------
def _worker_step(args) -> Tuple[Ant, ...]:
    chunk, all_ants, obstacles, width, height, dt, frame_tick = args
    return step_chunk(chunk, all_ants, obstacles, width, height, dt, frame_tick)


# ---------------------------------------------------------------------------
# 2 y 3. Mapeo paralelo + sincronización/consolidación
# ---------------------------------------------------------------------------
def update_parallel(
    state: GameState,
    dt: float,
    pool: mp.pool.Pool,
    n_workers: int,
) -> GameState:
    """Avanza un frame de simulación repartiendo el cálculo entre
    `n_workers` procesos del Pool recibido.

    Sincronización: pool.map() es bloqueante por diseño -> el proceso
    padre espera (join implícito) hasta que TODOS los workers retornan
    antes de continuar. No se renderiza ni se avanza el tick hasta que
    la consolidación está completa, cumpliendo el requisito de "esperar
    la finalización de los cálculos antes de avanzar".
    """
    chunks = _partition_ants(state.ants, n_workers)

    tasks = [
        (chunk, state.ants, state.obstacles, state.width, state.height, dt, state.tick)
        for chunk in chunks
    ]

    # map() bloquea hasta tener TODOS los resultados (sincronización).
    results: List[Tuple[Ant, ...]] = pool.map(_worker_step, tasks)

    # Consolidación: concatenar las tuplas resultantes en el mismo
    # orden en que se partieron (los chunks son contiguos por id).
    new_ants: Tuple[Ant, ...] = tuple(ant for chunk_result in results for ant in chunk_result)

    return state.with_ants(new_ants)


def update_sequential(state: GameState, dt: float) -> GameState:
    """Misma transformación pura (step_chunk) pero ejecutada en un solo
    proceso, sin Pool. Sirve como línea base para medir el speedup
    real del modo paralelo."""
    new_ants = step_chunk(
        state.ants, state.ants, state.obstacles, state.width, state.height, dt, state.tick
    )
    return state.with_ants(new_ants)


# ---------------------------------------------------------------------------
# Utilidades de configuración
# ---------------------------------------------------------------------------
def detect_total_cores() -> int:
    """Número total de núcleos lógicos detectados en la máquina."""
    return os.cpu_count() or 1


def recommended_worker_count() -> int:
    """Estrategia de número de workers: núcleos totales menos uno,
    dejando un núcleo libre para el hilo principal (render + I/O del
    sistema operativo), con un mínimo de 1.

    Esto se expone como dato técnico a justificar en la sustentación:
    no usamos TODOS los núcleos para evitar saturar la máquina y
    degradar el hilo de render/eventos de Arcade.
    """
    cores = detect_total_cores()
    return max(1, cores - 1)
