# Ctrl+J investigation

To confirm that Return (Enter) and `Ctrl+J` now arrive as distinct key codes in
all supported environments, run `prototype/key_probe.py` inside each terminal
context. The probe enables `curses.raw()`/`curses.nonl()` so we see unmodified
input.

```bash
python prototype/key_probe.py
```

Press `Enter`, then `Ctrl+J`, and finally `Esc` to exit. The script prints the
captured codes after it exits so they can be copied straight into docs.

## Raw sequences captured (Jan 2026)

| Environment | Return / Enter | Ctrl+J | Notes |
|-------------|----------------|--------|-------|
| Bare terminal (kitty 0.32, Linux) | `13 / 0x000d / KEY_ENTER` | `10 / 0x000a / ^J` | With newline translation disabled we receive carriage return for Enter. |
| tmux 3.4 (default settings) | `13 / 0x000d / KEY_ENTER` | `10 / 0x000a / ^J` | `Ctrl+J` remains a plain line-feed; Enter still resolves to carriage return. |
| tmux 3.4 with `set -g escape-time 0` | `13 / 0x000d / KEY_ENTER` | `10 / 0x000a / ^J` | Escape delay tweaks do not affect the codes after `curses.nonl()`. |

These measurements align with Vim’s behaviour: Enter yields carriage return,
while `Ctrl+J` stays a line-feed, even inside tmux.

## Manual verification checklist

1. Launch `o` in a bare terminal session. Ensure it boots into list mode.
2. Press `Enter` – the layout toggles (list ↔ matrix) and status message reflects the switch.
3. Press `Ctrl+J` repeatedly – selection jumps roughly 10 % downward; layout remains unchanged.
4. Enter filter mode (`/pattern`) and verify:
   - `Enter` applies the filter and exits filter mode.
   - `Ctrl+J` keeps the filter UI active and moves the selection.
5. Repeat steps 1–4 inside tmux (default) and again after running `set -g escape-time 0` to confirm identical behaviour.

No further tmux configuration is required once the application is running with
the updated curses initialisation.
