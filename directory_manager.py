# ~/Apps/vios/directory_manager.py
import os
import fnmatch
import subprocess
from typing import Optional, Dict, List, Set, Tuple


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""
        self.show_hidden = False  # Default: hide dotfiles/dotdirs
        self.sort_mode = "alpha"
        self.sort_map = {}
        self._cache: Dict[str, List[Tuple[str, bool]]] = {}
        self._git_repo_cache: Dict[str, Optional[str]] = {}
        self._git_ignored_cache: Dict[str, Tuple[Set[str], Set[str]]] = {}

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
            return "~" + real_path[len(real_home) :]
        return path

    def toggle_hidden(self):
        """Toggle visibility of hidden files/directories"""
        self.show_hidden = not self.show_hidden
        # Hidden visibility affects every cached listing, so clear caches
        self.refresh_cache()

    def get_hidden_status_text(self) -> str:
        """Return text for status bar when hidden files are visible"""
        return " .dot" if self.show_hidden else ""

    def get_items(self):
        real_path = os.path.realpath(self.current_path)
        cached = self._cache.get(real_path)
        if cached is not None:
            return cached[:]
        items = self.list_directory(self.current_path)
        self._cache[real_path] = items[:]
        return items

    def list_directory(self, target_path: str):
        try:
            raw_items = os.listdir(target_path)
        except (PermissionError, FileNotFoundError):
            return []

        visible_items = []

        real_target = os.path.realpath(target_path)
        sort_mode = self.sort_map.get(real_target, self.sort_mode)
        ignored_items = self._get_git_ignored_items(target_path, raw_items)

        for item in raw_items:
            if item in {".", ".."}:
                continue

            full_path = os.path.join(target_path, item)
            if not os.path.exists(full_path):
                continue

            is_dir = os.path.isdir(full_path)
            is_hidden = item.startswith(".")

            if is_hidden and not self.show_hidden:
                continue
            if item in ignored_items:
                continue

            visible_items.append((item, is_dir))

        if sort_mode == "alpha":
            visible_items.sort(key=self._alpha_sort_key)
        else:
            reverse = sort_mode == "mtime_desc"
            visible_items.sort(
                key=self._mtime_sort_key_factory(target_path), reverse=reverse
            )

        real_path = os.path.realpath(target_path)
        self._cache[real_path] = visible_items[:]
        return visible_items

    def _get_git_ignored_items(self, target_path: str, raw_items: List[str]) -> set:
        real_target = os.path.realpath(target_path)
        repo_root = self._get_git_repo_root(real_target)
        if not repo_root:
            return set()

        ignored_dirs, ignored_files = self._get_git_ignored_paths(repo_root)
        if not ignored_dirs and not ignored_files:
            return set()

        ignored_items = set()
        for item in raw_items:
            full_path = os.path.join(real_target, item)
            if not os.path.exists(full_path):
                continue
            rel_path = os.path.relpath(full_path, repo_root)
            if os.path.isdir(full_path):
                if f"{rel_path}/" in ignored_dirs:
                    ignored_items.add(item)
            elif rel_path in ignored_files:
                ignored_items.add(item)
        return ignored_items

    def _get_git_ignored_paths(self, repo_root: str) -> Tuple[Set[str], Set[str]]:
        cached = self._git_ignored_cache.get(repo_root)
        if cached is not None:
            return cached

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    repo_root,
                    "ls-files",
                    "--others",
                    "-i",
                    "--exclude-standard",
                    "--directory",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError):
            cached = (set(), set())
            self._git_ignored_cache[repo_root] = cached
            return cached

        if result.returncode != 0:
            cached = (set(), set())
            self._git_ignored_cache[repo_root] = cached
            return cached

        ignored_dirs: Set[str] = set()
        ignored_files: Set[str] = set()
        for line in result.stdout.splitlines():
            path = line.strip()
            if not path:
                continue
            normalized = path.replace("\\", "/")
            if normalized.endswith("/"):
                ignored_dirs.add(normalized)
            else:
                ignored_files.add(normalized)

        cached = (ignored_dirs, ignored_files)
        self._git_ignored_cache[repo_root] = cached
        return cached

    def _get_git_repo_root(self, target_path: str) -> Optional[str]:
        cached = self._git_repo_cache.get(target_path)
        if target_path in self._git_repo_cache:
            return cached

        for known_path, known_root in self._git_repo_cache.items():
            if not known_root:
                continue
            if target_path == known_root or target_path.startswith(f"{known_root}{os.sep}"):
                self._git_repo_cache[target_path] = known_root
                return known_root

        try:
            result = subprocess.run(
                ["git", "-C", target_path, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError):
            self._git_repo_cache[target_path] = None
            return None

        if result.returncode != 0:
            self._git_repo_cache[target_path] = None
            return None

        repo_root = result.stdout.strip() or None
        self._git_repo_cache[target_path] = repo_root
        return repo_root

    def _normalize_pattern(self, pattern: str) -> str:
        pattern = pattern.strip()
        if not pattern or pattern == "/":
            return ""
        if any(c in pattern for c in "*?[]"):
            return pattern
        return pattern + "*"

    def _split_patterns(self, pattern: str) -> List[str]:
        raw = pattern.replace(";", ",")
        parts = [part.strip() for part in raw.split(",")]
        return [part for part in parts if part]

    def get_filtered_items(self):
        all_items = self.get_items()

        if not self.filter_pattern:
            return all_items

        # Remove leading '/' used for visual feedback
        search_pattern = (
            self.filter_pattern[1:]
            if self.filter_pattern.startswith("/")
            else self.filter_pattern
        )

        if not search_pattern:
            return all_items

        normalized = self._normalize_pattern(search_pattern)
        patterns = self._split_patterns(normalized)
        if not patterns:
            return all_items

        lowered = [self._normalize_pattern(p).lower() for p in patterns if p]

        return [
            item
            for item in all_items
            if any(fnmatch.fnmatch(item[0].lower(), pat) for pat in lowered)
        ]

    def set_sort_mode(self, mode: str):
        if mode in {"alpha", "mtime_asc", "mtime_desc"}:
            if self.sort_mode == mode:
                return
            self.sort_mode = mode
            self.refresh_cache()

    def set_sort_mode_for_path(self, path: str, mode: str):
        if mode not in {"alpha", "mtime_asc", "mtime_desc"}:
            return
        if not path:
            return
        real_path = os.path.realpath(path)
        self.sort_map[real_path] = mode
        self._cache.pop(real_path, None)

    def refresh_cache(self, path: Optional[str] = None):
        if path:
            real = os.path.realpath(path)
            self._cache.pop(real, None)
        else:
            self._cache.clear()
        self._git_repo_cache.clear()
        self._git_ignored_cache.clear()

    def _alpha_sort_key(self, entry):
        name, is_dir = entry
        hidden = name.startswith(".")
        if hidden:
            group = 2 if is_dir else 3
        else:
            group = 0 if is_dir else 1
        return (group, name.lower())

    def _mtime_sort_key_factory(self, base_path: str):
        def sorter(entry):
            name, _ = entry
            full_path = os.path.join(base_path, name)
            try:
                mtime = os.path.getmtime(full_path)
            except Exception:
                mtime = 0
            return (mtime, name.lower())

        return sorter
