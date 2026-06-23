"""
ANDY QUIMI
render/app.py
==============
Capa de presentación (Arcade). Esta es la ÚNICA parte del proyecto que
tiene "estado mutable" visible para el usuario final — pero esa
mutabilidad vive exclusivamente en la clase de la ventana (que arcade
exige por diseño), NUNCA en el GameState ni en las entidades, que
siguen siendo inmutables en todo momento. La ventana simplemente
sostiene una REFERENCIA al GameState más reciente; en cada frame esa
referencia se REEMPLAZA por un GameState nuevo, nunca se muta el
contenido del que ya existía.

Controles:
  [P] Alternar entre modo PARALELO y SECUENCIAL en caliente.
  [UP]/[DOWN] Aumentar/disminuir el número de hormigas simuladas.
  [ESC] Salir.

Persona responsable sugerida: Integrante D (Render y Métricas de Rendimiento).
"""

from __future__ import annotations
import multiprocessing as mp
import time

import arcade

from core.state import make_initial_state, GameState
from core.parallel_engine import (
    update_parallel,
    update_sequential,
    detect_total_cores,
    recommended_worker_count,
)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Colonia de Hormigas — Enjambre Paralelo (multiprocessing)"

ANT_COLOR = arcade.color.DARK_BROWN
OBSTACLE_COLOR = arcade.color.DARK_SPRING_GREEN
HUD_COLOR = arcade.color.WHITE

DT = 1 / 60.0
INITIAL_ANTS = 800


class AntSwarmWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK_OLIVE)

        self.n_workers = recommended_worker_count()
        self.total_cores = detect_total_cores()
        self.pool = mp.Pool(processes=self.n_workers)

        self.parallel_mode = True
        self.state: GameState = make_initial_state(INITIAL_ANTS, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Métricas de HUD (no forman parte del GameState de simulación;
        # son puramente de presentación/diagnóstico).
        self._frame_times = []
        self._last_time = time.perf_counter()
        self.current_fps = 0.0

    # ------------------------------------------------------------------
    # Ciclo de actualización: aquí se invoca la capa funcional pura.
    # La ventana NO calcula física; solo pide un GameState nuevo y lo
    # reemplaza.
    # ------------------------------------------------------------------
    def on_update(self, delta_time: float):
        frame_start = time.perf_counter()

        if self.parallel_mode:
            self.state = update_parallel(self.state, DT, self.pool, self.n_workers)
        else:
            self.state = update_sequential(self.state, DT)

        frame_elapsed = time.perf_counter() - frame_start
        self._frame_times.append(frame_elapsed)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        avg = sum(self._frame_times) / len(self._frame_times)
        self.current_fps = 1.0 / avg if avg > 0 else 0.0

    # ------------------------------------------------------------------
    # Render: pura lectura del GameState, cero mutación.
    # ------------------------------------------------------------------
    def on_draw(self):
        self.clear()

        for obs in self.state.obstacles:
            arcade.draw_circle_filled(obs.x, obs.y, obs.radius, OBSTACLE_COLOR)

        for ant in self.state.ants:
            arcade.draw_circle_filled(ant.x, ant.y, 2.6, ANT_COLOR)

        mode_str = "PARALELO" if self.parallel_mode else "SECUENCIAL"
        workers_str = f"{self.n_workers} workers" if self.parallel_mode else "1 núcleo"

        hud_lines = [
            f"Modo: {mode_str} ({workers_str})  |  Núcleos totales: {self.total_cores}",
            f"Hormigas: {len(self.state.ants):,}   FPS: {self.current_fps:.1f}",
            "[P] Alternar modo   [UP/DOWN] +/- hormigas   [ESC] Salir",
        ]
        for i, line in enumerate(hud_lines):
            arcade.draw_text(line, 12, SCREEN_HEIGHT - 22 - i * 20, HUD_COLOR, 13)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.P:
            self.parallel_mode = not self.parallel_mode
        elif key == arcade.key.UP:
            self._resize_swarm(len(self.state.ants) + 500)
        elif key == arcade.key.DOWN:
            self._resize_swarm(max(0, len(self.state.ants) - 500))
        elif key == arcade.key.ESCAPE:
            arcade.close_window()

    def _resize_swarm(self, new_count: int):
        self.state = make_initial_state(new_count, SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_close(self):
        self.pool.close()
        self.pool.join()
        super().on_close()


def main():
    window = AntSwarmWindow()
    arcade.run()


if __name__ == "__main__":
    main()
