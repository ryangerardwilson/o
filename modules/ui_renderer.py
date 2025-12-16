# ~/Apps/vios/modules/ui_renderer.py
import curses
import os

from .directory_manager import pretty_path


class UIRenderer:
    def __init__(self, navigator):
        self.nav = navigator
        self.stdscr = None  # Will be set in core_navigator.run()

    def render(self):
        if not self.stdscr:
            return
        stdscr = self.stdscr

        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()

        # Current path at top
        display_path = pretty_path(self.nav.dir_manager.current_path)
        try:
            stdscr.addstr(0, max(0, (max_x - len(display_path)) // 2),
                          display_path[:max_x], curses.color_pair(2))
            stdscr.clrtoeol()
        except curses.error:
            pass

        # Help screen
        if self.nav.show_help:
            lines = self.nav.cheatsheet.strip().split('\n')
            for i, line in enumerate(lines[:max_y-2]):
                try:
                    attr = curses.color_pair(5) | curses.A_BOLD if "CHEATSHEET" in line else curses.color_pair(2)
                    stdscr.addstr(i + 1, 2, line, attr)
                except curses.error:
                    pass

        # File browser or completion list
        elif self.nav.show_file_list or self.nav.completion.in_completion:
            items, selected, total = self._get_display_items()
            height = max_y - 3
            for i in range(min(height, total)):
                name, is_dir = items[i]
                prefix = "> " if i == selected else "  "
                color = curses.color_pair(1) | curses.A_BOLD if i == selected else curses.color_pair(2)
                try:
                    stdscr.addstr(2 + i, 2, f"{prefix}{name}"[:max_x-3], color)
                    stdscr.clrtoeol()
                except curses.error:
                    pass
            if total == 0:
                msg = "(no matches)" if self.nav.completion.in_completion else "(empty directory)"
                try:
                    stdscr.addstr(max_y//2, max(0, (max_x - len(msg))//2), msg, curses.color_pair(2))
                except curses.error:
                    pass

        # Status/command line at bottom
        mode_text = "[HJKL]" if self.nav.hjkl_mode else "[TERM]"
        comp_text = " [Completing]" if self.nav.completion.in_completion else ""
        help_text = " [Help]" if self.nav.show_help else ""
        yank_text = (f"  CUT: {self.nav.clipboard.yanked_original_name}"
                     f"{'/' if self.nav.clipboard.yanked_is_dir else ''}"
                     if self.nav.clipboard.yanked_temp_path else "")

        status = f"{mode_text}{comp_text}{help_text} {self.nav.command_buffer}{yank_text}"
        status_color = (curses.color_pair(5) | curses.A_BOLD
                        if self.nav.hjkl_mode or self.nav.completion.in_completion or self.nav.show_help
                        else curses.color_pair(3))

        try:
            stdscr.addstr(max_y - 1, 0, status[:max_x-1], status_color)
            stdscr.clrtoeol()
        except curses.error:
            pass

        # Cursor management — ONLY in normal terminal mode
        if (self.nav.hjkl_mode or self.nav.show_help or self.nav.completion.in_completion):
            curses.curs_set(0)
        else:
            curses.curs_set(1)
            prompt_len = len(f"{mode_text}{comp_text}{help_text} ")
            cursor_x = prompt_len + self.nav.cursor_pos
            try:
                stdscr.move(max_y - 1, min(cursor_x, max_x - 1))
            except curses.error:
                pass  # Safe to ignore if position is off-screen

        stdscr.refresh()

    def _get_display_items(self):
        if self.nav.completion.in_completion and self.nav.completion.matches:
            base_dir = self.nav.completion.base_dir
            matches = self.nav.completion.matches
            items = []
            for rel_name in matches:
                full_path = os.path.join(self.nav.dir_manager.current_path, base_dir, rel_name.rstrip("/"))
                items.append((rel_name, os.path.isdir(full_path)))
            return items, self.nav.completion.selected, len(items)
        else:
            items = self.nav.dir_manager.get_filtered_items()
            return items, self.nav.browser_selected, len(items)
