# ~/Apps/vios/modules/directory_manager.py
import os
import fnmatch


def pretty_path(path: str) -> str:
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):] if path != home else "~"
    return path


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""  # Raw pattern as typed by user

    def change_directory(self, new_path: str):
        new_path = os.path.realpath(os.path.expanduser(new_path))
        if os.path.isdir(new_path):
            self.current_path = new_path
            self.filter_pattern = ""  # Always clear on explicit cd
            return True
        return False

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
        except PermissionError:
            return []

        items_with_info = []
        for item in items:
            if item.startswith("."):
                continue
            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            items_with_info.append((item, is_dir))

        items_with_info.sort(key=lambda x: (not x[1], x[0].lower()))
        return items_with_info

    def _normalize_pattern(self, pattern: str) -> str:
        if not pattern:
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def get_filtered_items(self):
        all_items = self.get_items()
        raw_pattern = self.filter_pattern
        if not raw_pattern:
            return all_items
        pattern = self._normalize_pattern(raw_pattern).lower()
        return [
            item for item in all_items
            if fnmatch.fnmatch(item[0].lower(), pattern)
        ]
