# ~/Apps/vios/modules/core_navigator.py
import curses
import subprocess
import os
import sys

from .directory_manager import DirectoryManager
from .clipboard_manager import ClipboardManager
from .ui_renderer import UIRenderer
from .input_handler import InputHandler
from .constants import Constants


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()

        self.renderer = UIRenderer(self)
        self.input_handler = InputHandler(self)

        self.show_help = False
        self.browser_selected = 0
        self.list_offset = 0
        self.need_redraw = True

        # Multi-mark support — now using full absolute paths
        self.marked_items = set()  # set of str (absolute paths)

        self.cheatsheet = Constants.CHEATSHEET

    def open_file(self, filepath: str):
        import mimetypes

        curses.endwin()

        try:
            mime_type, _ = mimetypes.guess_type(filepath)
            if mime_type == 'application/pdf':
                subprocess.Popen([
                    "zathura", filepath
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid
                )
            else:
                subprocess.call([
                    "vim",
                    "-c", f"cd {self.dir_manager.current_path}",
                    filepath
                ])
        except FileNotFoundError:
            pass
        finally:
            self.need_redraw = True

    def open_terminal(self):
        current_dir = self.dir_manager.current_path
        cd_command = f"cd \"{current_dir}\""

        try:
            subprocess.run(
                ["wl-copy", cd_command],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        raise KeyboardInterrupt

    def create_new_file(self):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New file: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)         # block indefinitely for user input
            curses.echo()
            curses.curs_set(1)

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            stdscr.move(prompt_y, input_x)
            filename_bytes = stdscr.getstr(prompt_y, input_x, max_input_width)
            filename = filename_bytes.decode('utf-8', errors='ignore').strip()
        except KeyboardInterrupt:
            filename = ""
        except Exception:
            filename = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
            stdscr.timeout(40)         # restore run()'s timeout
            self.need_redraw = True

        if not filename:
            return

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, filename)
        filepath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            with open(filepath, 'w'):
                pass
            os.utime(filepath, None)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating file: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

        # Open the newly created file in Vim
        self.open_file(filepath)

    def create_new_directory(self):
        stdscr = self.renderer.stdscr
        if not stdscr:
            return

        max_y, max_x = stdscr.getmaxyx()

        if max_y < 2 or max_x < 20:
            curses.flash()
            self.need_redraw = True
            return

        prompt = "New dir: "
        prompt_y = max_y - 1

        stdscr.move(prompt_y, 0)
        stdscr.clrtoeol()

        try:
            stdscr.addstr(prompt_y, 0, prompt[:max_x-1])
        except curses.error:
            pass

        try:
            stdscr.timeout(-1)         # block indefinitely for user input
            curses.echo()
            curses.curs_set(1)

            input_x = len(prompt)
            max_input_width = max_x - input_x - 1
            if max_input_width < 10:
                max_input_width = 10

            stdscr.move(prompt_y, input_x)
            dirname_bytes = stdscr.getstr(prompt_y, input_x, max_input_width)
            dirname = dirname_bytes.decode('utf-8', errors='ignore').strip()
        except KeyboardInterrupt:
            dirname = ""
        except Exception:
            dirname = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
            stdscr.timeout(40)         # restore run()'s timeout
            self.need_redraw = True

        if not dirname:
            return

        unique_name = self.input_handler._get_unique_name(self.dir_manager.current_path, dirname)
        dirpath = os.path.join(self.dir_manager.current_path, unique_name)

        try:
            os.makedirs(dirpath)
        except Exception as e:
            stdscr.addstr(prompt_y, 0, f"Error creating dir: {str(e)[:max_x-20]}", curses.A_BOLD)
            stdscr.clrtoeol()
            stdscr.refresh()
            stdscr.getch()
            return

    def run(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, 6):
            curses.init_pair(i, [curses.COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_YELLOW,
                                 curses.COLOR_RED, curses.COLOR_GREEN][i-1], -1)

        self.renderer.stdscr = stdscr

        try:
            stdscr.keypad(True)
            stdscr.leaveok(True)
            stdscr.idlok(True)
        except Exception:
            pass

        stdscr.timeout(40)

        while True:
            if self.need_redraw:
                self.renderer.render()
                self.need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue

            if self.input_handler.handle_key(stdscr, key):
                break

            self.need_redraw = True
