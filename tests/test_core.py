"""
tests/test_core.py
====================
Pruebas que sustentan, con evidencia ejecutable, dos afirmaciones clave
que el equipo deberá defender oralmente:

  1. El estado es verdaderamente inmutable (no hay mutación oculta).
  2. El modo paralelo y el modo secuencial producen el MISMO resultado
     numérico dado el mismo estado inicial -> el paralelismo no altera
     la lógica de negocio, solo la velocidad de ejecución.

Ejecutar con:
    pytest tests/ -v
"""

import multiprocessing as mp
import pytest

from core.state import make_initial_state, Ant
from core.parallel_engine import update_sequential, update_parallel


def test_state_is_frozen():
    """Un GameState y sus Ant no se pueden mutar in-place."""
    state = make_initial_state(10)
    with pytest.raises(Exception):
        state.tick = 99  # debe lanzar FrozenInstanceError
    with pytest.raises(Exception):
        state.ants[0].x = 0.0  # debe lanzar FrozenInstanceError


def test_sequential_does_not_mutate_original_state():
    """update_sequential debe retornar un GameState NUEVO; el original
    no cambia jamás."""
    state = make_initial_state(20)
    original_tick = state.tick
    original_first_ant_x = state.ants[0].x

    new_state = update_sequential(state, 1 / 60)

    assert state.tick == original_tick
    assert state.ants[0].x == original_first_ant_x
    assert new_state.tick == original_tick + 1


def test_sequential_and_parallel_produce_identical_results():
    """Dado el mismo estado inicial, un paso secuencial y un paso
    paralelo (con 3 workers) deben producir EXACTAMENTE las mismas
    posiciones de hormigas. Esto demuestra que el paralelismo es
    correcto, no solo rápido."""
    state_seq = make_initial_state(137, seed=7)  # número "feo" a propósito
    state_par = make_initial_state(137, seed=7)

    next_seq = update_sequential(state_seq, 1 / 60)

    with mp.Pool(processes=3) as pool:
        next_par = update_parallel(state_par, 1 / 60, pool, 3)

    assert len(next_seq.ants) == len(next_par.ants)
    for a_seq, a_par in zip(next_seq.ants, next_par.ants):
        assert a_seq.id == a_par.id
        assert a_seq.x == pytest.approx(a_par.x)
        assert a_seq.y == pytest.approx(a_par.y)
        assert a_seq.vx == pytest.approx(a_par.vx)
        assert a_seq.vy == pytest.approx(a_par.vy)


def test_partition_covers_all_ants_without_duplicates():
    from core.parallel_engine import _partition_ants

    ants = tuple(Ant(id=i, x=0, y=0, vx=0, vy=0, heading=0) for i in range(101))
    chunks = _partition_ants(ants, n_workers=4)

    all_ids = [ant.id for chunk in chunks for ant in chunk]
    assert sorted(all_ids) == list(range(101))  # todas presentes, sin duplicados
    assert len(chunks) <= 4
