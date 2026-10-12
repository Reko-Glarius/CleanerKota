#########################################
# Libraries
#########################################
import argparse
import ctypes
import json
import logging
import math
from pathlib import Path
import threading
import time

#########################################
# Constants
#########################################
BASE_DIR = Path(__file__).resolve().parent

#########################################
# Functions
#########################################
def move_smoothly(pdi, stop, x, y, duration):
    """Recorre una línea con entradas intermedias durante duration segundos."""
    start_x, start_y = pdi.position()
    started = time.monotonic()
    while not stop.is_set():
        progress = min((time.monotonic() - started) / duration, 1.0)
        pdi.moveTo(
            round(start_x + (x - start_x) * progress),
            round(start_y + (y - start_y) * progress),
            _pause=False,
        )
        if progress >= 1.0:
            return
        stop.wait(min(0.01, max(0, duration - (time.monotonic() - started))))


def load_pattern(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    points = data.get("points")
    if not isinstance(points, list) or not points:
        raise ValueError("PENDIENTE: registra el patrón con record_clicks.py primero.")
    for point in points:
        if not isinstance(point, dict) or any(
            not isinstance(point.get(key), int) or isinstance(point.get(key), bool)
            for key in ("x", "y")
        ):
            raise ValueError("Cada punto debe contener coordenadas enteras x e y.")
    return points, data.get("screen_size")


#########################################
# Main
#########################################
def create_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", type=Path, default=BASE_DIR / "pattern.json")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--move-duration", type=float, default=0.3, help="Segundos de desplazamiento por tramo (por defecto 0.3)")
    parser.add_argument("--point-delay", type=float, default=0, help="Pausa adicional al llegar a cada punto")
    parser.add_argument("--save-timeout", type=float, default=15)
    parser.add_argument("--hold-left", action="store_true", help="Mantener clic izquierdo durante el patrón")
    parser.add_argument("--once", action="store_true", help="Completar un solo ciclo")
    return parser


def validate_options(args):
    values = (args.threshold, args.point_delay, args.save_timeout, args.move_duration)
    if not all(math.isfinite(value) for value in values) or not 0 < args.threshold <= 1 or args.point_delay < 0 or args.save_timeout <= 0 or args.move_duration <= 0:
        raise ValueError("Umbral entre 0 y 1; demora >= 0, duración > 0 y timeout > 0. Todos deben ser finitos.")


def run_bot(args, stop=None):
    """Motor compartido por la consola y la interfaz gráfica."""
    validate_options(args)
    if stop is None:
        stop = threading.Event()

    ctypes.windll.user32.SetProcessDPIAware()
    import cv2
    import numpy as np
    import pyautogui as pg
    import pydirectinput as pdi
    from pynput import keyboard

    points, recorded_size = load_pattern(args.pattern)
    if recorded_size and list(pg.size()) != recorded_size:
        raise ValueError("La resolución cambió. Vuelve a grabar el patrón.")
    templates = {}
    for name in ("dirty", "add"):
        path = BASE_DIR / "resource" / f"{name}.png"
        template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise ValueError(f"No se pudo leer {path}")
        templates[name] = template

    listener = keyboard.Listener(on_press=lambda key: stop.set() if key == keyboard.Key.f8 else None)
    listener.start()
    pdi.FAILSAFE = True

    def wait(seconds):
        return stop.wait(seconds)

    def detect(name):
        frame = cv2.cvtColor(np.array(pg.screenshot()), cv2.COLOR_RGB2GRAY)
        template = templates[name]
        h, w = template.shape
        if h > frame.shape[0] or w > frame.shape[1]:
            raise ValueError(f"La plantilla {name} es mayor que la pantalla.")
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, confidence, _, location = cv2.minMaxLoc(result)
        if confidence >= args.threshold:
            return location[0] + w // 2, location[1] + h // 2
        return None

    try:
        logging.info("Inicio en 5 segundos. F8 para detener; esquina superior izquierda como emergencia.")
        if wait(5):
            return
        while not stop.is_set():
            if detect("dirty") is None:
                wait(0.25)
                continue
            logging.info("Objeto sucio detectado. Esperando 0.25 segundos.")
            if wait(0.25):
                break
            if detect("dirty") is None:
                continue
            # Los clics grabados son destinos: aquí se mueve el mouse en ese orden.
            pdi.moveTo(points[0]["x"], points[0]["y"])
            try:
                if args.hold_left:
                    pdi.mouseDown()
                for point in points[1:]:
                    if stop.is_set():
                        break
                    move_smoothly(pdi, stop, point["x"], point["y"], args.move_duration)
                    if wait(args.point_delay):
                        break
            finally:
                if args.hold_left:
                    pdi.mouseUp()
            if stop.is_set() or wait(0.25):
                break
            logging.info("Buscando botón de guardar.")
            deadline = time.monotonic() + args.save_timeout
            saved = False
            while not stop.is_set() and time.monotonic() < deadline:
                button = detect("add")
                if button:
                    if stop.is_set():
                        break
                    pdi.click(*button)
                    saved = True
                    logging.info("Botón de guardar pulsado.")
                    break
                wait(0.25)
            if not saved:
                logging.warning("No se encontró el botón. Se detiene para evitar repetir el patrón.")
                break
            if args.once:
                break
            logging.info("Esperando 0.1 segundos antes de volver a buscar suciedad.")
            if wait(0.1):
                break
    finally:
        stop.set()
        listener.stop()
        logging.info("Bot detenido.")


def main():
    parser = create_parser()
    args = parser.parse_args()
    try:
        validate_options(args)
    except ValueError as error:
        parser.error(str(error))
    run_bot(args)


#########################################
# Start Code
#########################################
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Detenido con Ctrl+C.")
    except (ValueError, OSError) as error:
        logging.error("%s", error)
        raise SystemExit(1)
