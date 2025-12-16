# ~/Apps/vios/modules/core_navigator.py
import curses
import subprocess
import os

from .directory_manager import DirectoryManager, pretty_path
from .clipboard_manager import ClipboardManager
from .ui_renderer import UIRenderer
from .input_handler import InputHandler


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False  # Hidden by default
        self.browser_selected = 0
        self.need_redraw = True

        self.cheatsheet = r"""
VIOS CHEATSHEET

Navigation
  h               Parent directory (resets filter)
  l / Enter       Enter directory (resets filter) or open file
  j               Down
  k               Up

Filtering (glob-style)
  /               Enter filter mode (type pattern)
                  • "rat" → matches items starting with "rat"
                  • "*.py" → all Python files
                  • "*test*" → contains "test"
                  • Press Enter to apply and persist filter
                  • Press / again or Esc to cancel and clear
  Ctrl+R          Clear filter and show all items

Clipboard
  y               Start yank (copy) — yy to confirm
  d               Start cut/delete — dd to confirm
  Backspace/Del   Immediate cut selected item
  p               Paste (auto-rename on conflict)
  Ctrl+L          Clear clipboard

File Opening
  • Text files (.py, .txt, .md, etc.) → Vim
  • PDF files → Zathura

Other
  t               Open terminal in current directory
  ?               Toggle this help
  q / Esc         Quit the app
"""

    def open_file(self, filepath: str):
        """Open file with appropriate external program (Vim for text, Zathura for PDF)."""
        import mimetypes

        mime_type, _ = mimetypes.guess_type(filepath)

        curses.endwin()  # Restore terminal before launching external app

        try:
            if mime_type == 'application/pdf':
                # Open PDF with Zathura (detached)
                subprocess.Popen([
                    "zathura", filepath
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid
                )
            else:
                # Assume text or fallback to Vim
                subprocess.call([
                    "vim",
                    "-c", f"cd {self.dir_manager.current_path}",
                    filepath
                ])
        except FileNotFoundError:
            # If app not found, just continue silently
            pass
        finally:
            self.need_redraw = True

    def open_terminal(self):
        try:
            # Open Alacritty in current directory, fully detached
            subprocess.Popen([
                "setsid", "alacritty",
                "--working-directory", self.dir_manager.current_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
            )
        except FileNotFoundError:
            try:
                # Fallback: generic terminal emulator
                subprocess.Popen([
                    "setsid", "x-terminal-emulator",
                    "-e", f"cd {self.dir_manager.current_path} && exec $SHELL"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
                )
            except FileNotFoundError:
                curses.flash()
        self.need_redraw = True

    def run(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)

        self.renderer.stdscr = stdscr

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if self.input_handler.handle_key(stdscr, key):
                break  # Quit

            self.need_redraw = True
