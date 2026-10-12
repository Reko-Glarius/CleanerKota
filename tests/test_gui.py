import threading
import tkinter as tk
import unittest
from unittest.mock import patch

from gui import CleanerKotaApp


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.window = tk.Tk()
        self.window.withdraw()
        self.app = CleanerKotaApp(self.window)

    def tearDown(self):
        self.app.close()
        if self.app.worker is not None:
            self.app.worker.join(timeout=3)
        self.app.poll()

    def test_start_stop_and_restart(self):
        started = threading.Event()

        def fake_bot(args, stop):
            started.set()
            stop.wait(2)

        with patch("gui.run_bot", side_effect=fake_bot) as bot:
            self.app.values["threshold"].set("0,7")
            self.app.start()
            self.assertTrue(started.wait(1))
            self.app.start()
            self.assertEqual(bot.call_count, 1)
            self.assertEqual(bot.call_args.args[0].threshold, 0.7)
            self.assertEqual(str(self.app.start_button["state"]), "disabled")
            self.app.request_stop()
            self.app.worker.join(timeout=3)
            self.app.poll()
            self.assertIsNone(self.app.worker)
            self.assertEqual(str(self.app.start_button["state"]), "normal")
            self.app.start()
            self.app.request_stop()
            self.app.worker.join(timeout=3)
            self.app.poll()
            self.assertEqual(bot.call_count, 2)

    def test_invalid_options_do_not_start_worker(self):
        self.app.values["move_duration"].set("0")
        with patch("gui.messagebox.showerror") as error, patch("gui.run_bot") as bot:
            self.app.start()
        error.assert_called_once()
        bot.assert_not_called()
        self.assertIsNone(self.app.worker)

    def test_close_signals_worker_before_destroying_window(self):
        def fake_bot(args, stop):
            stop.wait(2)

        with patch("gui.run_bot", side_effect=fake_bot):
            self.app.start()
            self.app.close()
            self.assertTrue(self.app.stop.is_set())
            self.assertEqual(self.window.winfo_exists(), 1)
            self.app.worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
