# Resultados de Rendimiento

- **Núcleos totales detectados:** 8
- **Workers (procesos) configurados:** 7
- **Estrategia de partición:** bloques contiguos de tamaño `ceil(N / n_workers)` aplicados sobre la tupla inmutable de hormigas.

| Cantidad de Entidades | Rendimiento Secuencial (1 Núcleo) | Rendimiento Paralelo (7 Núcleos) | Speedup |
|---|---|---|---|
| 1,000 | 3.54 FPS | 6.71 FPS | 1.90x |
| 3,000 | 0.42 FPS | 0.80 FPS | 1.92x |
| 5,000 | 0.13 FPS | 0.30 FPS | 2.37x |
