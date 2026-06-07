"""Unit tests for pure integration logic."""

from datetime import timedelta
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "mg_saic"
    / "logic.py"
)
SPEC = importlib.util.spec_from_file_location("mg_saic_logic", MODULE_PATH)
LOGIC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(LOGIC)


class NormalizeSunroofActionTests(unittest.TestCase):
    def test_accepts_boolean_true(self):
        self.assertEqual(LOGIC.normalize_sunroof_action(True), (True, "open"))

    def test_accepts_boolean_false(self):
        self.assertEqual(LOGIC.normalize_sunroof_action(False), (False, "close"))

    def test_accepts_string(self):
        self.assertEqual(LOGIC.normalize_sunroof_action("open"), (True, "open"))

    def test_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            LOGIC.normalize_sunroof_action("tilt")


class SelectUpdateIntervalTests(unittest.TestCase):
    def setUp(self):
        self.default_interval = timedelta(minutes=30)
        self.powered_interval = timedelta(minutes=1)
        self.charging_interval = timedelta(minutes=5)
        self.grace_interval = timedelta(minutes=10)
        self.after_shutdown_interval = timedelta(minutes=20)

    def select_interval(self, **kwargs):
        return LOGIC.select_update_interval(
            default_update_interval=self.default_interval,
            powered_update_interval=self.powered_interval,
            charging_update_interval=self.charging_interval,
            grace_period_update_interval=self.grace_interval,
            after_shutdown_update_interval=self.after_shutdown_interval,
            **kwargs,
        )

    def test_prefers_powered_interval(self):
        interval = self.select_interval(
            is_powered_on=True,
            is_charging=False,
            idle_duration=timedelta(hours=1),
            activity_duration=timedelta(hours=1),
        )
        self.assertEqual(interval, self.powered_interval)

    def test_prefers_charging_interval(self):
        interval = self.select_interval(
            is_powered_on=False,
            is_charging=True,
            idle_duration=timedelta(hours=1),
            activity_duration=timedelta(hours=1),
        )
        self.assertEqual(interval, self.charging_interval)

    def test_uses_grace_period_interval_for_recent_activity(self):
        interval = self.select_interval(
            is_powered_on=False,
            is_charging=False,
            idle_duration=timedelta(hours=1),
            activity_duration=timedelta(minutes=5),
        )
        self.assertEqual(interval, self.grace_interval)

    def test_uses_after_shutdown_interval_before_default(self):
        interval = self.select_interval(
            is_powered_on=False,
            is_charging=False,
            idle_duration=timedelta(minutes=15),
            activity_duration=timedelta(hours=1),
        )
        self.assertEqual(interval, self.after_shutdown_interval)

    def test_preserves_user_default_interval_when_idle(self):
        interval = self.select_interval(
            is_powered_on=False,
            is_charging=False,
            idle_duration=timedelta(hours=1),
            activity_duration=timedelta(hours=1),
        )
        self.assertEqual(interval, self.default_interval)


if __name__ == "__main__":
    unittest.main()
