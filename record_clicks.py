"""Registra clics izquierdos en orden. F8 termina y guarda el patrón."""

import argparse
import ctypes
import json
from pathlib import Path
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "pattern.json")
    args = parser.parse_args()
    ctypes.windll.user32.SetProcessDPIAware()
    import pyautogui as pg
    from pynput import keyboard, mouse

    points = []
    stop = threading.Event()

    def on_click(x, y, button, pressed):
        if pressed and button == mouse.Button.left and not stop.is_set():
            points.append({"x": int(x), "y": int(y)})
            print(f"Punto {len(points)}: ({int(x)}, {int(y)})", flush=True)

    def on_key(key):
        if key == keyboard.Key.f8:
            stop.set()
            return False

    print("Abre el juego. El registro comienza en 5 segundos.")
    time.sleep(5)
    print("Haz clic en cada punto del patrón. Pulsa F8 para guardar y terminar.")
    mouse_listener = mouse.Listener(on_click=on_click)
    key_listener = keyboard.Listener(on_press=on_key)
    mouse_listener.start()
    key_listener.start()
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        mouse_listener.stop()
        key_listener.stop()
        mouse_listener.join()
        key_listener.join()
    if not points:
        print("No se registraron puntos. El archivo existente se conserva.")
        return
    data = {"screen_size": list(pg.size()), "points": points}
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Guardados {len(points)} puntos en {args.output.resolve()}")


if __name__ == "__main__":
    main()
