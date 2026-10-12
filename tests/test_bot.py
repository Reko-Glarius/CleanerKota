import contextlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import main


class FakeStop:
    def __init__(self):
        self.stopped = False
        self.now = 0
        self.waits = []

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.waits.append(seconds)
        self.now += seconds
        return self.stopped


class BotTests(unittest.TestCase):
    def test_pattern_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            pattern = Path(directory) / "pattern.json"
            for points in ([], [{"x": True, "y": 1}], [{"x": 1.5, "y": 1}]):
                pattern.write_text(json.dumps({"points": points}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    main.load_pattern(pattern)

    def test_nonfinite_options_rejected(self):
        for name in ("threshold", "point_delay", "move_duration", "save_timeout"):
            for value in (float("nan"), float("inf")):
                args = main.create_parser().parse_args([])
                setattr(args, name, value)
                with self.assertRaises(ValueError):
                    main.validate_options(args)

    def run_fake_bot(self, scores, hold=False, fail_move=False, cancel_on_click=False, once=True):
        args = main.create_parser().parse_args(["--once", "--save-timeout", "0.5"])
        args.once = once
        args.hold_left = hold
        stop = FakeStop()
        pdi = Mock()
        if cancel_on_click:
            pdi.click.side_effect = lambda *args: stop.set()
        cv = Mock()
        image = types.SimpleNamespace(shape=(10, 10))
        cv.imread.return_value = image
        cv.cvtColor.return_value = types.SimpleNamespace(shape=(1080, 1920))
        cv.minMaxLoc.side_effect = [(0, score, (0, 0), (100, 200)) for score in scores]
        pg = Mock()
        pg.size.return_value = (1920, 1080)
        keyboard = Mock()
        modules = {"cv2": cv, "numpy": Mock(), "pyautogui": pg, "pydirectinput": pdi, "pynput": types.SimpleNamespace(keyboard=keyboard)}
        move = Mock(side_effect=RuntimeError("Movimiento fallido") if fail_move else None)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict("sys.modules", modules))
            stack.enter_context(patch.object(main.ctypes, "windll", create=True))
            stack.enter_context(patch.object(main.time, "monotonic", side_effect=lambda: stop.now))
            stack.enter_context(patch.object(main, "load_pattern", return_value=([{"x": 20, "y": 30}, {"x": 40, "y": 50}], [1920, 1080])))
            stack.enter_context(patch.object(main, "move_smoothly", move))
            if fail_move:
                with self.assertRaises(RuntimeError):
                    main.run_bot(args, stop)
            else:
                main.run_bot(args, stop)
        keyboard.Listener.return_value.stop.assert_called_once()
        self.assertTrue(stop.is_set())
        return pdi, move, stop, keyboard

    def test_one_cycle_preserves_route_and_timings(self):
        pdi, move, stop, _ = self.run_fake_bot([1, 1, 1], hold=True)
        pdi.moveTo.assert_called_once_with(20, 30)
        move.assert_called_once_with(pdi, stop, 40, 50, 0.3)
        pdi.mouseDown.assert_called_once()
        pdi.mouseUp.assert_called_once()
        pdi.click.assert_called_once_with(105, 205)
        self.assertEqual(stop.waits, [5, 0.25, 0, 0.25])

    def test_missing_save_button_stops(self):
        pdi, _, stop, _ = self.run_fake_bot([1, 1, 0, 0])
        pdi.click.assert_not_called()
        self.assertEqual(stop.waits[-2:], [0.25, 0.25])

    def test_mouse_released_on_error(self):
        pdi, _, _, _ = self.run_fake_bot([1, 1], hold=True, fail_move=True)
        pdi.mouseUp.assert_called_once()
        pdi.click.assert_not_called()

    def test_continuous_mode_keeps_delay_after_save(self):
        pdi, _, stop, _ = self.run_fake_bot([1, 1, 1], cancel_on_click=True, once=False)
        pdi.click.assert_called_once()
        self.assertEqual(stop.waits[-1], 0.1)

    def test_dirty_must_still_be_visible(self):
        pdi, move, stop, _ = self.run_fake_bot([1, 0, 1, 1, 1])
        self.assertEqual(stop.waits[:3], [5, 0.25, 0.25])
        move.assert_called_once()
        pdi.click.assert_called_once()

    def test_smooth_move_sends_intermediate_positions(self):
        stop = FakeStop()
        pdi = Mock()
        pdi.position.return_value = (0, 0)
        with patch.object(main.time, "monotonic", side_effect=lambda: stop.now):
            main.move_smoothly(pdi, stop, 100, 50, 0.03)
        self.assertGreater(pdi.moveTo.call_count, 2)
        self.assertEqual(pdi.moveTo.call_args_list[0].args, (0, 0))
        pdi.moveTo.assert_called_with(100, 50, _pause=False)

    def test_cancel_before_start(self):
        stop = FakeStop()
        stop.set()
        modules = {name: Mock() for name in ("cv2", "numpy", "pyautogui", "pydirectinput", "pynput")}
        with patch.dict("sys.modules", modules), patch.object(main.ctypes, "windll", create=True), patch.object(main, "load_pattern", return_value=([{"x": 1, "y": 2}], None)):
            main.run_bot(main.create_parser().parse_args([]), stop)
        modules["pydirectinput"].moveTo.assert_not_called()
        modules["pydirectinput"].click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
