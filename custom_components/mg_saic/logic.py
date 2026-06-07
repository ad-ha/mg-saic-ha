"""Pure logic helpers used by the integration.

These helpers deliberately avoid Home Assistant imports so they can be tested
with the standard library only.
"""

from datetime import timedelta


def normalize_sunroof_action(action):
    """Normalize a sunroof action to `(should_open, action_name)`."""
    if isinstance(action, bool):
        return action, "open" if action else "close"

    action_name = str(action).lower()
    if action_name not in {"open", "close"}:
        raise ValueError(
            f"Invalid sunroof action '{action}'. Expected 'open' or 'close'."
        )

    return action_name == "open", action_name


def select_update_interval(
    *,
    is_powered_on,
    is_charging,
    idle_duration,
    activity_duration,
    default_update_interval,
    powered_update_interval,
    charging_update_interval,
    grace_period_update_interval,
    after_shutdown_update_interval,
):
    """Return the interval that should be used for the current state."""
    if is_powered_on:
        return powered_update_interval

    if is_charging:
        return charging_update_interval

    if (
        activity_duration <= grace_period_update_interval
        or idle_duration <= grace_period_update_interval
    ):
        return grace_period_update_interval

    if idle_duration <= after_shutdown_update_interval:
        return after_shutdown_update_interval

    if not isinstance(default_update_interval, timedelta):
        raise TypeError("default_update_interval must be a timedelta")

    return default_update_interval
