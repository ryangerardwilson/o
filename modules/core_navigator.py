# ~/Apps/vios/modules/core_navigator.py
import curses
import subprocess

from .directory_manager import DirectoryManager, pretty_path, is_text_file
from .clipboard_manager import ClipboardManager
from .command_processor import CommandProcessor
from .ui_renderer import UIRenderer
from .input_handler import InputHandler
from .completion_manager import CompletionManager


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()
        self.cmd_processor = CommandProcessor(self.dir_manager, self._open_in_vim)

        self.completion = CompletionManager(self.dir_manager)
        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.hjkl_mode = False
        self.show_file_list = False
        self.show_help = False

        self.command_buffer = ""
        self.cursor_pos = 0

        # Command history
        self.history = []
        self.history_index = -1
        self.current_input = ""

        self.browser_selected = 0

        # Redraw control
        self.need_redraw = True

        self.cheatsheet = r"""
VIOS CHEATSHEET

Global
  Ctrl+D          Toggle file browser visibility
  help            Show this cheatsheet

Terminal Mode ([TERM])
  Tab             File/directory completion
  Ctrl+P / Ctrl+N Cycle command history
  Ctrl+A / Ctrl+E Go to beginning/end of line
  Ctrl+W          Delete word left
  Alt+D           Delete word right
  Backspace       Delete char left
  Ctrl+D          Delete char right
  hjkl + Enter    Enter HJKL navigation mode (shows browser)

HJKL Mode ([HJKL])
  h               Go to parent directory
  l / Enter       Enter directory or open file
  j / k           Move down/up
  t               Open terminal here
  Ctrl+L          Clear yank (cut)
  Esc             Return to terminal mode

Completion Mode
  Tab / Esc       Close completion
  h               Go up one directory level
  l               Drill into directory (if dir) or select file
  Enter           Accept current directory path

Press any key to close...
"""

    def _open_in_vim(self, filepath: str):
        curses.endwin()
        try:
            subprocess.call([
                "vim",
                "-c", f"cd {self.dir_manager.current_path}",
                filepath
            ])
        except FileNotFoundError:
            pass
        finally:
            # Ensure screen is refreshed on return
            self.need_redraw = True

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["alacritty", "--working-directory", self.dir_manager.current_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            curses.flash()
        self.need_redraw = True

    def run(self, stdscr):
        curses.curs_set(1)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)
        stdscr.bkgd(" ", curses.color_pair(2))
        stdscr.nodelay(True)

        self.renderer.stdscr = stdscr  # Give renderer access to stdscr

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            self.input_handler.handle_key(stdscr, key)
            self.need_redraw = True  # Nearly all inputs change display state
