"""Mini interfaz de CleanerKota. Ejecuta el mismo motor que main.py."""

import ctypes
import logging
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from main import BASE_DIR, create_parser, load_pattern, run_bot, validate_options


class QueueHandler(logging.Handler):
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
        self.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        self.messages.put(("log", self.format(record)))


class CleanerKotaApp:
    def __init__(self, window):
        self.window = window
        self.worker = None
        self.stop = threading.Event()
        self.messages = queue.Queue()
        self.closing = False
        defaults = create_parser().parse_args([])
        # Un patrón junto al EXE permite personalizarlo sin recompilar.
        external_pattern = Path(sys.executable).parent / "pattern.json"
        pattern = external_pattern if getattr(sys, "frozen", False) and external_pattern.is_file() else defaults.pattern

        window.title("CleanerKota")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="CleanerKota", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Inicia el bot y vuelve al juego en 5 segundos.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 12))

        self.controls = []
        self.pattern = tk.StringVar(value=str(pattern))
        ttk.Label(frame, text="Patrón").grid(row=2, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=self.pattern, width=35)
        entry.grid(row=2, column=1, sticky="ew", padx=8)
        browse = ttk.Button(frame, text="Elegir…", command=self.choose_pattern)
        browse.grid(row=2, column=2)
        self.controls.extend((entry, browse))
        self.values = {}
        for row, (name, label) in enumerate((
            ("threshold", "Similitud mínima"),
            ("move_duration", "Segundos por tramo"),
            ("point_delay", "Pausa por punto (s)"),
            ("save_timeout", "Espera de guardar (s)"),
        ), start=3):
            variable = tk.StringVar(value=str(getattr(defaults, name)))
            self.values[name] = variable
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(frame, textvariable=variable, width=12)
            entry.grid(row=row, column=1, sticky="w", padx=8)
            self.controls.append(entry)

        self.hold_left = tk.BooleanVar(value=False)
        self.once = tk.BooleanVar(value=False)
        for row, text, variable in ((7, "Mantener clic izquierdo", self.hold_left), (8, "Completar un solo ciclo", self.once)):
            control = ttk.Checkbutton(frame, text=text, variable=variable)
            control.grid(row=row, column=0, columnspan=3, sticky="w", pady=3)
            self.controls.append(control)

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=3, sticky="w", pady=12)
        self.start_button = ttk.Button(buttons, text="Comenzar", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Detener", command=self.request_stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.status = tk.StringVar(value="Listo")
        ttk.Label(frame, textvariable=self.status).grid(row=10, column=0, columnspan=3, sticky="w")
        self.log = ScrolledText(frame, width=65, height=9, state="disabled", font=("Consolas", 9))
        self.log.grid(row=11, column=0, columnspan=3, pady=(8, 0))
        ttk.Label(frame, text="F8 detiene el bot. Emergencia: cursor en la esquina superior izquierda.").grid(row=12, column=0, columnspan=3, pady=(8, 0))

        self.handler = QueueHandler(self.messages)
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.INFO)
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.after(100, self.poll)

    def choose_pattern(self):
        selected = filedialog.askopenfilename(parent=self.window, title="Elegir patrón", filetypes=[("Patrón JSON", "*.json")])
        if selected:
            self.pattern.set(selected)

    def start(self):
        if self.worker is not None:
            return
        args = create_parser().parse_args([])
        try:
            for name, variable in self.values.items():
                setattr(args, name, float(variable.get().replace(",", ".")))
            args.pattern = Path(self.pattern.get())
            args.hold_left = self.hold_left.get()
            args.once = self.once.get()
            validate_options(args)
            if not args.pattern.is_file():
                raise ValueError("Elige un archivo de patrón existente.")
        except (ValueError, OSError) as error:
            messagebox.showerror("Revisa la configuración", str(error), parent=self.window)
            return
        self.stop = threading.Event()
        self.set_running(True)
        self.status.set("En ejecución: vuelve al juego. F8 para detener.")
        self.worker = threading.Thread(target=self.run, args=(args, self.stop), daemon=False)
        self.worker.start()

    def run(self, args, stop):
        try:
            run_bot(args, stop)
        except Exception as error:
            logging.exception("El bot se detuvo por un error.")
            self.messages.put(("error", str(error)))

    def set_running(self, running):
        for control in self.controls:
            control.configure(state="disabled" if running else "normal")
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def request_stop(self):
        self.stop.set()
        self.status.set("Deteniendo…")
        self.stop_button.configure(state="disabled")

    def close(self):
        self.closing = True
        self.request_stop()
        self.start_button.configure(state="disabled")
        # poll espera a que el motor libere el botón del mouse y termine.

    def poll(self):
        while True:
            try:
                kind, text = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "error" and not self.closing:
                messagebox.showerror("CleanerKota", text, parent=self.window)
            elif kind == "log":
                self.log.configure(state="normal")
                self.log.insert("end", text + "\n")
                # Mantener acotado el historial en sesiones largas.
                if int(self.log.index("end-1c").split(".")[0]) > 500:
                    self.log.delete("1.0", "2.0")
                self.log.see("end")
                self.log.configure(state="disabled")
        if self.worker is not None and not self.worker.is_alive():
            self.worker.join()
            self.worker = None
            if not self.closing:
                self.set_running(False)
                self.status.set("Detenido. Puedes volver a comenzar.")
        if self.closing and self.worker is None:
            logging.getLogger().removeHandler(self.handler)
            self.window.destroy()
            return
        self.window.after(100, self.poll)


def main():
    # Configurar DPI antes de crear la ventana o importar librerías de captura.
    ctypes.windll.user32.SetProcessDPIAware()
    window = tk.Tk()
    app = CleanerKotaApp(window)
    if sys.argv[1:] == ["--smoke-test"]:
        # Verificar el paquete sin mover el cursor ni iniciar el bot.
        import cv2
        import numpy
        import pyautogui
        import pydirectinput
        from PIL import ImageGrab
        from pynput import keyboard, mouse

        load_pattern(BASE_DIR / "pattern.json")
        for name in ("dirty", "add"):
            if cv2.imread(str(BASE_DIR / "resource" / f"{name}.png")) is None:
                raise ValueError(f"Falta la imagen de referencia {name}.")
        window.withdraw()
        window.after(200, app.close)
    window.mainloop()


if __name__ == "__main__":
    if sys.argv[1:] == ["--smoke-test"]:
        try:
            main()
        except Exception:
            # La verificación automatizada debe fallar sin un diálogo bloqueante.
            sys.exit(1)
    else:
        main()
