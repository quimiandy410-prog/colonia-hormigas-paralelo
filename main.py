"""
main.py
========
Punto de entrada. Lanza la ventana interactiva de Arcade.

    python main.py

Dentro de la ventana:
  [P]         alterna entre modo PARALELO y SECUENCIAL en caliente
  [UP]/[DOWN] aumenta/disminuye el número de hormigas simuladas
  [ESC]       cierra la simulación

Para el benchmark formal (tabla de FPS comparativa), usar en su lugar:

    python -m bench.benchmark
"""

from render.app import main

if __name__ == "__main__":
    main()
