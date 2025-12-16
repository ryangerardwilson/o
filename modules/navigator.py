# ~/Apps/vios/modules/navigator.py
import curses
import os
import subprocess
import shutil

from .directory_manager import DirectoryManager, is_text_file, pretty_path
from .clipboard_manager import ClipboardManager
from .command_processor import CommandProcessor


class FileNavigator:
    def __init__(self, start_path: str):
        self.dir_manager = DirectoryManager(start_path)
        self.clipboard = ClipboardManager()
        self.cmd_processor = CommandProcessor(self.dir_manager, self._open_in_vim)

        self.command_mode = False          # True = navigating with hjkl, False = typing commands
        self.show_file_list = False       # Hidden by default — toggle with Ctrl+D
        self.command_buffer = ""
        self.completion_matches = []
        self.completion_index = 0
        self.selected = 0

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

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["alacritty", "--working-directory", self.dir_manager.current_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            curses.flash()

    def prompt_new_name(self, stdscr, original_name: str) -> str | None:
        curses.curs_set(1)
        stdscr.nodelay(False)
        max_y, max_x = stdscr.getmaxyx()
        curses.echo()

        prompt = f"Name exists: {original_name} -> New name: "
        input_str = original_name

        while True:
            stdscr.clear()
            try:
                stdscr.addstr(max_y//2 - 1, max(0, (max_x - len(prompt + input_str))//2),
                              prompt + input_str, curses.A_BOLD)
                stdscr.addstr(max_y//2 + 1, max(0, (max_x - 40)//2),
                              "Enter = confirm, ESC = cancel", curses.color_pair(2))
            except curses.error:
                pass
            stdscr.refresh()

            key = stdscr.getch()
            if key in (10, 13):
                new_name = input_str.strip()
                if new_name:
                    curses.noecho()
                    curses.curs_set(0)
                    stdscr.nodelay(True)
                    return new_name
            elif key == 27:
                break
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                input_str = input_str[:-1]
            elif 32 <= key <= 126:
                input_str += chr(key)

        curses.noecho()
        curses.curs_set(0)
        stdscr.nodelay(True)
        return None

    def run(self, stdscr):
        curses.curs_set(1)  # Cursor visible for typing
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        stdscr.bkgd(" ", curses.color_pair(2))
        stdscr.nodelay(True)

        need_redraw = True

        while True:
            items = self.dir_manager.get_filtered_items()
            total_items = len(items)
            if self.selected >= total_items:
                self.selected = max(0, total_items - 1)

            max_y, max_x = stdscr.getmaxyx()

            if need_redraw:
                stdscr.clear()

                # Top line: current path (always visible)
                display_path = pretty_path(self.dir_manager.current_path)
                try:
                    stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                                  display_path[:max_x], curses.color_pair(2))
                    stdscr.clrtoeol()
                except curses.error:
                    pass

                # File browser area — only shown when toggled on
                if self.show_file_list:
                    available_height = max_y - 3  # Leave space for path + command line
                    if total_items > 0:
                        for i in range(min(available_height, total_items)):
                            name, is_dir = items[i]
                            display_name = name + "/" if is_dir else name
                            prefix = "> " if i == self.selected and self.command_mode else "  "
                            color = (curses.color_pair(1) | curses.A_BOLD
                                     if i == self.selected and self.command_mode
                                     else curses.color_pair(2))
                            try:
                                stdscr.addstr(2 + i, 2, f"{prefix}{display_name}"[:max_x - 3], color)
                                stdscr.clrtoeol()
                            except curses.error:
                                pass
                    else:
                        msg = "(empty directory)" if os.access(self.dir_manager.current_path, os.R_OK) else "(permission denied)"
                        try:
                            stdscr.addstr(max_y // 2, max(0, (max_x - len(msg)) // 2), msg, curses.color_pair(2))
                        except curses.error:
                            pass

                # Bottom command line — always visible
                mode_text = "[CMD]" if self.command_mode else "[TERM]"
                browser_text = " [Browser]" if self.show_file_list else ""
                yank_text = ""
                if self.clipboard.yanked_temp_path:
                    yank_text = f"  CUT: {self.clipboard.yanked_original_name}{'/' if self.clipboard.yanked_is_dir else ''}"

                status_line = f"{mode_text}{browser_text} {self.command_buffer}{yank_text}"
                try:
                    stdscr.addstr(max_y - 1, 0, status_line[:max_x - 1],
                                  curses.color_pair(5) | curses.A_BOLD if self.command_mode else curses.color_pair(3))
                    stdscr.clrtoeol()
                except curses.error:
                    pass

                # Cursor at end of command buffer
                cursor_pos = len(f"{mode_text}{browser_text} {self.command_buffer}")
                try:
                    stdscr.move(max_y - 1, min(cursor_pos, max_x - 1))
                except curses.error:
                    pass

                stdscr.refresh()
                need_redraw = False

            key = stdscr.getch()
            if key == -1:
                continue
            need_redraw = True

            # Global: Toggle file browser visibility
            if key == 4:  # Ctrl+D
                self.show_file_list = not self.show_file_list
                # When hiding browser, go back to terminal mode
                if not self.show_file_list:
                    self.command_mode = False
                    curses.curs_set(1)
                continue

            # Global: Toggle command mode — only allowed when browser is visible
            if key == 23:  # Ctrl+W
                if self.show_file_list:
                    self.command_mode = not self.command_mode
                    curses.curs_set(0 if self.command_mode else 1)
                else:
                    curses.flash()  # Not allowed when browser hidden
                continue

            # If browser is hidden → pure terminal mode only
            if not self.show_file_list:
                self.command_mode = False
                curses.curs_set(1)

            # Command Mode: navigation with hjkl (only when browser visible)
            if self.command_mode and self.show_file_list:
                if key == ord('t'):
                    self.open_terminal()

                elif key == 12:  # Ctrl+L
                    self.clipboard.cleanup()

                elif key in (curses.KEY_UP, ord("k")):
                    if total_items > 0:
                        self.selected = (self.selected - 1) % total_items

                elif key in (curses.KEY_DOWN, ord("j")):
                    if total_items > 0:
                        self.selected = (self.selected + 1) % total_items

                elif key in (curses.KEY_LEFT, ord("h")):
                    parent = os.path.dirname(self.dir_manager.current_path)
                    if parent != self.dir_manager.current_path:
                        self.dir_manager.current_path = parent
                        self.selected = 0

                elif key in (curses.KEY_RIGHT, ord("l"), 10, 13):
                    if total_items == 0:
                        continue
                    name, is_dir = items[self.selected]
                    path = os.path.join(self.dir_manager.current_path, name)
                    if is_dir:
                        self.dir_manager.current_path = path
                        self.selected = 0
                    elif is_text_file(path):
                        self._open_in_vim(path)
                    else:
                        curses.flash()

                elif key == 27:  # ESC
                    self.clipboard.cleanup()
                    return

                continue  # Skip terminal input handling in command mode

            # Terminal Mode: typing commands
            if key in (10, 13):  # Enter
                cmd = self.command_buffer.strip()
                self.command_buffer = ""
                self.completion_matches = []
                self.completion_index = 0
                if cmd:
                    self.cmd_processor.run_shell_command(cmd)

            elif key == 9:  # Tab
                parts = self.command_buffer.rstrip().split()
                if parts:
                    partial = parts[-1]
                    matches = self.dir_manager.get_tab_completions(partial)
                    if matches:
                        if len(matches) == 1:
                            parts[-1] = matches[0]
                            self.command_buffer = " ".join(parts) + " "
                        else:
                            if self.completion_matches != matches:
                                self.completion_matches = matches
                                self.completion_index = 0
                            else:
                                self.completion_index = (self.completion_index + 1) % len(matches)
                            parts[-1] = self.completion_matches[self.completion_index]
                            self.command_buffer = " ".join(parts) + " "

            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.command_buffer = self.command_buffer[:-1]
                self.completion_matches = []

            elif 32 <= key <= 126:
                self.command_buffer += chr(key)
                self.completion_matches = []
