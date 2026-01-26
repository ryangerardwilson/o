"""Centralised key constants and helpers for keyboard handling."""

from __future__ import annotations

import curses


# Distinguish between carriage return (Enter/Return key) and line feed (Ctrl+J).
KEY_CTRL_J: int = 10
KEY_ENTER_CARRIAGE: int = 13


# Some terminals surface "Enter" as curses.KEY_ENTER, others as carriage return.
try:
    _CURSES_KEY_ENTER = curses.KEY_ENTER
except AttributeError:  # pragma: no cover - platform specific
    _CURSES_KEY_ENTER = None


# Alias sets for quick membership tests.
ENTER_KEY_CODES: set[int] = {KEY_ENTER_CARRIAGE}
if _CURSES_KEY_ENTER is not None:
    ENTER_KEY_CODES.add(_CURSES_KEY_ENTER)


# Ctrl+J commonly surfaces as ASCII line-feed (10); Shift+Down can map to KEY_SF.
try:
    _CURSES_KEY_SHIFT_DOWN = curses.KEY_SF
except AttributeError:  # pragma: no cover - platform specific
    _CURSES_KEY_SHIFT_DOWN = None


CTRL_J_KEY_CODES: set[int] = {KEY_CTRL_J}
if _CURSES_KEY_SHIFT_DOWN is not None:
    CTRL_J_KEY_CODES.add(_CURSES_KEY_SHIFT_DOWN)


def is_enter(key: int) -> bool:
    """Return True when *key* represents the Enter/Return key."""

    return key in ENTER_KEY_CODES


def is_ctrl_j(key: int) -> bool:
    """Return True when *key* represents Ctrl+J or equivalent gestures."""

    return key in CTRL_J_KEY_CODES
