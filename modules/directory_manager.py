# ~/Apps/vios/modules/directory_manager.py
import os
import fnmatch


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""
        self.show_hidden = False  # Default: hide dotfiles/dotdirs

        # Keep home_path for pretty_path only
        self.home_path = os.path.realpath(os.path.expanduser("~"))

    @classmethod
    def pretty_path(cls, path: str) -> str:
        """Convert absolute path to pretty ~ form if it's under home."""
        home = os.path.expanduser("~")
        real_home = os.path.realpath(home)
        real_path = os.path.realpath(path)

        if real_path.startswith(real_home):
            if real_path == real_home:
                return "~"
            return "~" + real_path[len(real_home):]
        return path

    def toggle_hidden(self):
        """Toggle visibility of hidden files/directories"""
        self.show_hidden = not self.show_hidden

    def get_hidden_status_text(self) -> str:
        """Return text for status bar when hidden files are visible"""
        return " .dot" if self.show_hidden else ""

    def get_items(self):
        try:
            raw_items = os.listdir(self.current_path)
        except PermissionError:
            return []

        visible_items = []

        for item in raw_items:
            if item in {".", ".."}:
                continue

            full_path = os.path.join(self.current_path, item)
            if not os.path.exists(full_path):
                continue

            is_dir = os.path.isdir(full_path)
            is_hidden = item.startswith(".")

            # Simple rule: show hidden items only if toggle is on
            if is_hidden and not self.show_hidden:
                continue

            # Everything else (non-hidden, or hidden+toggle on) is visible
            visible_items.append((item, is_dir))

        # Sorting: non-dot dirs → non-dot files → dot dirs → dot files
        def sort_key(entry):
            name, is_dir = entry
            hidden = name.startswith(".")
            if hidden:
                group = 2 if is_dir else 3
            else:
                group = 0 if is_dir else 1
            return (group, name.lower())

        visible_items.sort(key=sort_key)

        return visible_items

    def _normalize_pattern(self, pattern: str) -> str:
        pattern = pattern.strip()
        if not pattern or pattern == "/":
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def get_filtered_items(self):
        all_items = self.get_items()

        if not self.filter_pattern:
            return all_items

        # Remove leading '/' used for visual feedback
        search_pattern = self.filter_pattern[1:] if self.filter_pattern.startswith("/") else self.filter_pattern

        if not search_pattern:
            return all_items

        normalized = self._normalize_pattern(search_pattern)
        pattern_lower = normalized.lower()

        return [
            item for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern_lower)
        ]
