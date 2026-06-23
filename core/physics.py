"""
JEAN CARLOS ALEJANDRO DE LA CRUZ
core/physics.py
================
Funciones PURAS de física y comportamiento. Ninguna función de este
módulo muta su entrada: todas reciben datos y retornan datos nuevos.

Comportamiento implementado: "evasión de obstáculos tipo enjambre".
Cada hormiga:
  1. Mantiene una dirección de "deambular" (wander) con ruido leve.
  2. Se repele de los obstáculos cercanos (steering de evasión).
  3. Se repele levemente de las hormigas vecinas demasiado próximas
     (cohesión de enjambre sin colisión, tipo boids simplificado).
  4. Rebota en los bordes del mundo.

Esta es la función que se paraleliza: es la unidad de trabajo que cada
worker de multiprocessing ejecuta de forma masiva sobre su porción de
hormigas (ver core/parallel_engine.py).

Persona responsable sugerida: Integrante B (Física y Reglas de Comportamiento).
"""

from __future__ import annotations
from typing import Tuple
import math
import random

from core.state import Ant, Obstacle

MAX_SPEED = 70.0
WANDER_STRENGTH = 18.0
AVOID_RADIUS = 70.0
AVOID_STRENGTH = 320.0
NEIGHBOR_RADIUS = 26.0
NEIGHBOR_STRENGTH = 40.0


def _clamp_speed(vx: float, vy: float, max_speed: float = MAX_SPEED) -> Tuple[float, float]:
    speed = math.hypot(vx, vy)
    if speed > max_speed and speed > 0:
        scale = max_speed / speed
        return vx * scale, vy * scale
    return vx, vy


def _bounce(pos: float, vel: float, limit: float) -> Tuple[float, float]:
    """Rebote elástico simple contra un borde del mundo [0, limit]."""
    if pos < 0:
        return 0.0, abs(vel)
    if pos > limit:
        return limit, -abs(vel)
    return pos, vel


def _obstacle_repulsion(ant: Ant, obstacles: Tuple[Obstacle, ...]) -> Tuple[float, float]:
    """Calcula el vector de repulsión (fuerza de evasión) generado por
    todos los obstáculos cercanos a una hormiga. Pura: no modifica nada,
    solo retorna un vector (fx, fy)."""
    fx, fy = 0.0, 0.0
    for obs in obstacles:
        dx = ant.x - obs.x
        dy = ant.y - obs.y
        dist = math.hypot(dx, dy) - obs.radius
        threshold = AVOID_RADIUS
        if 0 < dist < threshold:
            push = AVOID_STRENGTH * (1.0 - dist / threshold) / max(dist, 1e-3)
            fx += dx * push
            fy += dy * push
        elif dist <= 0:
            # Dentro del obstáculo: empuje máximo hacia afuera.
            norm = math.hypot(dx, dy) or 1e-3
            fx += (dx / norm) * AVOID_STRENGTH
            fy += (dy / norm) * AVOID_STRENGTH
    return fx, fy


def _swarm_repulsion(ant: Ant, neighbors: Tuple[Ant, ...]) -> Tuple[float, float]:
    """Repulsión leve frente a vecinos muy próximos, para que el enjambre
    no colapse en un solo punto. `neighbors` es una porción acotada de
    hormigas (no todas), pasada explícitamente -> función pura sin estado
    compartido."""
    fx, fy = 0.0, 0.0
    for other in neighbors:
        if other.id == ant.id:
            continue
        dx = ant.x - other.x
        dy = ant.y - other.y
        dist = math.hypot(dx, dy)
        if 0 < dist < NEIGHBOR_RADIUS:
            push = NEIGHBOR_STRENGTH * (1.0 - dist / NEIGHBOR_RADIUS) / dist
            fx += dx * push
            fy += dy * push
    return fx, fy


def step_ant(
    ant: Ant,
    obstacles: Tuple[Obstacle, ...],
    neighbors: Tuple[Ant, ...],
    width: float,
    height: float,
    dt: float,
    rng_seed: int,
) -> Ant:
    """Función pura central: dado el estado actual de UNA hormiga más el
    contexto (obstáculos, vecinos, límites del mundo), retorna una
    hormiga NUEVA con posición/velocidad/heading actualizados.

    No muta `ant`: usa los valores leídos para construir un Ant() nuevo.
    `rng_seed` permite ruido determinista por hormiga y por frame, lo
    cual es importante para que el benchmark secuencial vs paralelo
    parta de las mismas condiciones de simulación.
    """
    local_rng = random.Random(rng_seed)

    # 1. Ruido de deambular (wander)
    wander_angle = local_rng.uniform(-0.5, 0.5)
    wx = math.cos(ant.heading + wander_angle) * WANDER_STRENGTH
    wy = math.sin(ant.heading + wander_angle) * WANDER_STRENGTH

    # 2. Evasión de obstáculos
    ox, oy = _obstacle_repulsion(ant, obstacles)

    # 3. Repulsión de enjambre (vecinos)
    nx, ny = _swarm_repulsion(ant, neighbors)

    # Integración simple de fuerzas -> nueva velocidad
    new_vx = ant.vx + (wx + ox + nx) * dt
    new_vy = ant.vy + (wy + oy + ny) * dt
    new_vx, new_vy = _clamp_speed(new_vx, new_vy)

    # Nueva posición
    new_x = ant.x + new_vx * dt
    new_y = ant.y + new_vy * dt

    # Rebote en bordes
    new_x, new_vx = _bounce(new_x, new_vx, width)
    new_y, new_vy = _bounce(new_y, new_vy, height)

    new_heading = math.atan2(new_vy, new_vx) if (new_vx or new_vy) else ant.heading

    return Ant(
        id=ant.id,
        x=new_x,
        y=new_y,
        vx=new_vx,
        vy=new_vy,
        heading=new_heading,
    )


def step_chunk(
    chunk: Tuple[Ant, ...],
    all_ants: Tuple[Ant, ...],
    obstacles: Tuple[Obstacle, ...],
    width: float,
    height: float,
    dt: float,
    frame_tick: int,
) -> Tuple[Ant, ...]:
    """Aplica `step_ant` a TODA una porción (chunk) de hormigas usando
    una comprensión de tupla (transformación declarativa, sin bucles
    destructivos ni mutación).

    Esta es exactamente la función que se envía a cada proceso worker:
    es pura (mismo input -> mismo output), no toca disco ni estado
    compartido, y por eso es 100% segura de paralelizar con
    multiprocessing sin locks ni semáforos.
    """
    return tuple(
        step_ant(
            ant,
            obstacles,
            all_ants,  # vecindario completo; en un proyecto más grande
                       # se filtraría por grid espacial, aquí se mantiene
                       # simple para que el costo por hormiga sea uniforme
                       # y el speedup paralelo sea claramente medible.
            width,
            height,
            dt,
            rng_seed=frame_tick * 1_000_003 + ant.id,
        )
        for ant in chunk
    )

