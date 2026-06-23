"""
core/state.py
==============
Define las estructuras de datos INMUTABLES del simulador.

Regla de arquitectura #1: el estado completo del juego vive en una única
estructura `GameState`, construida con @dataclass(frozen=True). Ninguna
variable global mutable existe en este módulo ni en el resto del proyecto.

Persona responsable sugerida: Integrante A (Estado y Modelo de Datos).
"""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Tuple
import math
import random


# ---------------------------------------------------------------------------
# Entidad: Hormiga
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ant:
    """Una hormiga individual. Inmutable: cada cambio de estado genera
    una instancia NUEVA mediante `dataclasses.replace`, nunca se mutan
    los atributos de una instancia existente."""

    id: int
    x: float
    y: float
    vx: float
    vy: float
    heading: float  # radianes, usado solo para el render (rotación del sprite)


# ---------------------------------------------------------------------------
# Entidad: Obstáculo estático (piedra, rama, etc.)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Obstacle:
    """Obstáculo circular estático que las hormigas deben evadir."""

    x: float
    y: float
    radius: float


# ---------------------------------------------------------------------------
# Estado global congelado
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GameState:
    """Estado completo e inmutable de la simulación en un instante dado.

    `ants` y `obstacles` son TUPLAS (no listas) precisamente para reforzar
    la inmutabilidad: una tupla no se puede mutar in-place, así que la
    única forma de "avanzar" el estado es construir un GameState nuevo.
    """

    ants: Tuple[Ant, ...]
    obstacles: Tuple[Obstacle, ...]
    width: float
    height: float
    tick: int = 0

    def with_ants(self, new_ants: Tuple[Ant, ...]) -> "GameState":
        """Devuelve un GameState NUEVO con las hormigas actualizadas.
        No modifica `self` en ningún momento (replace crea una copia)."""
        return replace(self, ants=new_ants, tick=self.tick + 1)


# ---------------------------------------------------------------------------
# Constructores / Factories puras
# ---------------------------------------------------------------------------
def make_initial_state(
    n_ants: int,
    width: float = 1200,
    height: float = 800,
    n_obstacles: int = 14,
    seed: int = 42,
) -> GameState:
    """Función pura: dado un número de hormigas y un seed, construye un
    GameState inicial determinista (mismo seed -> mismo estado inicial).
    Útil para que el benchmark sea reproducible entre modo secuencial
    y modo paralelo.
    """
    rng = random.Random(seed)

    ants = tuple(
        Ant(
            id=i,
            x=rng.uniform(0, width),
            y=rng.uniform(0, height),
            vx=rng.uniform(-60, 60),
            vy=rng.uniform(-60, 60),
            heading=rng.uniform(0, 2 * math.pi),
        )
        for i in range(n_ants)
    )

    obstacles = tuple(
        Obstacle(
            x=rng.uniform(60, width - 60),
            y=rng.uniform(60, height - 60),
            radius=rng.uniform(20, 45),
        )
        for _ in range(n_obstacles)
    )

    return GameState(ants=ants, obstacles=obstacles, width=width, height=height, tick=0)
