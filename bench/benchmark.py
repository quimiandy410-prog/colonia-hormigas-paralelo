"""
ANDY
bench/benchmark.py
====================
Genera la tabla comparativa exigida por el reto:

    Cantidad de Entidades | Rendimiento Secuencial (1 Núcleo) | Rendimiento Paralelo (N Núcleos)
    1,000 / 3,000 / 5,000 |                X FPS               |              Y FPS

Mide FPS REAL ejecutando N frames de simulación pura (sin ventana
gráfica, para que el benchmark no esté contaminado por el costo de
dibujar sprites) y reporta también:
  - núcleos totales detectados
  - número de workers activos
  - estrategia de partición usada

Uso:
    python -m bench.benchmark
    python -m bench.benchmark --frames 120 --sizes 1000 3000 5000

Persona responsable sugerida: Integrante D (Render y Métricas de Rendimiento),
en conjunto con Integrante C para la parte de configuración del Pool.
"""

from __future__ import annotations
import argparse
import time
import multiprocessing as mp
from typing import List

from core.state import make_initial_state
from core.parallel_engine import (
    update_sequential,
    update_parallel,
    detect_total_cores,
    recommended_worker_count,
)

DT = 1 / 60.0  # paso de simulación fijo, independiente del modo medido


def _run_sequential(n_ants: int, frames: int) -> float:
    """Ejecuta `frames` pasos de simulación en modo secuencial y
    retorna el FPS promedio sostenido."""
    state = make_initial_state(n_ants)
    start = time.perf_counter()
    for _ in range(frames):
        state = update_sequential(state, DT)
    elapsed = time.perf_counter() - start
    return frames / elapsed if elapsed > 0 else float("inf")


def _run_parallel(n_ants: int, frames: int, n_workers: int) -> float:
    """Ejecuta `frames` pasos de simulación en modo paralelo, reusando
    el mismo Pool durante todo el benchmark (crear procesos es costoso;
    crearlos una sola vez es coherente con un Game Loop real, donde el
    Pool se abre al iniciar el programa y se cierra al salir)."""
    state = make_initial_state(n_ants)
    with mp.Pool(processes=n_workers) as pool:
        start = time.perf_counter()
        for _ in range(frames):
            state = update_parallel(state, DT, pool, n_workers)
        elapsed = time.perf_counter() - start
    return frames / elapsed if elapsed > 0 else float("inf")


def run_benchmark(sizes: List[int], frames: int, n_workers: int) -> List[dict]:
    rows = []
    for n in sizes:
        seq_fps = _run_sequential(n, frames)
        par_fps = _run_parallel(n, frames, n_workers)
        speedup = par_fps / seq_fps if seq_fps > 0 else float("inf")
        rows.append(
            {
                "entidades": n,
                "fps_secuencial": seq_fps,
                "fps_paralelo": par_fps,
                "speedup": speedup,
            }
        )
    return rows


def print_report(rows: List[dict], n_workers: int) -> None:
    total_cores = detect_total_cores()
    print("=" * 78)
    print("REPORTE DE RENDIMIENTO — Simulación de Colonia de Hormigas")
    print("=" * 78)
    print(f"Núcleos totales detectados : {total_cores}")
    print(f"Workers (procesos) activos : {n_workers}")
    print("Estrategia de partición    : bloques contiguos de tamaño "
          "ceil(N / n_workers) sobre la tupla de hormigas")
    print("-" * 78)
    header = f"{'Entidades':>12} | {'Secuencial (1 núcleo)':>22} | {'Paralelo (' + str(n_workers) + ' núcleos)':>22} | {'Speedup':>8}"
    print(header)
    print("-" * 78)
    for row in rows:
        print(
            f"{row['entidades']:>12,} | "
            f"{row['fps_secuencial']:>19.2f} FPS | "
            f"{row['fps_paralelo']:>19.2f} FPS | "
            f"{row['speedup']:>7.2f}x"
        )
    print("=" * 78)


def save_markdown(rows: List[dict], n_workers: int, path: str) -> None:
    total_cores = detect_total_cores()
    lines = [
        "# Resultados de Rendimiento\n",
        f"- **Núcleos totales detectados:** {total_cores}",
        f"- **Workers (procesos) configurados:** {n_workers}",
        "- **Estrategia de partición:** bloques contiguos de tamaño "
        "`ceil(N / n_workers)` aplicados sobre la tupla inmutable de hormigas.\n",
        "| Cantidad de Entidades | Rendimiento Secuencial (1 Núcleo) | "
        f"Rendimiento Paralelo ({n_workers} Núcleos) | Speedup |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['entidades']:,} | {row['fps_secuencial']:.2f} FPS | "
            f"{row['fps_paralelo']:.2f} FPS | {row['speedup']:.2f}x |"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nTabla guardada en: {path}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark secuencial vs paralelo")
    parser.add_argument("--frames", type=int, default=120,
                         help="Número de frames de simulación medidos por caso")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 3000, 5000],
                         help="Cantidades de entidades a probar")
    parser.add_argument("--workers", type=int, default=None,
                         help="Número de workers paralelos (default: núcleos-1)")
    parser.add_argument("--output", type=str, default="bench/RESULTADOS.md",
                         help="Ruta del archivo markdown de salida")
    args = parser.parse_args()

    n_workers = args.workers or recommended_worker_count()

    print(f"Ejecutando benchmark con {args.frames} frames por caso, "
          f"workers={n_workers}, tamaños={args.sizes}...\n")

    rows = run_benchmark(args.sizes, args.frames, n_workers)
    print_report(rows, n_workers)
    save_markdown(rows, n_workers, args.output)


if __name__ == "__main__":
    main()
