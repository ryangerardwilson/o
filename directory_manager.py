# ~/Apps/vios/directory_manager.py
import os
import fnmatch
import subprocess
from typing import Optional, Dict, List, Tuple


class DirectoryManager:
    def __init__(self, start_path: str):
        self.current_path = os.path.realpath(start_path)
        self.filter_pattern = ""
        self.show_hidden = False  # Default: hide dotfiles/dotdirs
        self.sort_mode = "alpha"
        self.sort_map = {}
        self._cache: Dict[str, List[Tuple[str, bool]]] = {}
        self._git_repo_cache: Dict[str, Optional[str]] = {}
        self._oinclude_cache: Dict[str, List[str]] = {}
        self._nested_gitignore_cache: Dict[str, List[str]] = {}

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
        candidates: List[Tuple[str, str, str, bool]] = []
        for item in raw_items:
            full_path = os.path.join(real_target, item)
            if not os.path.exists(full_path):
                continue
            rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
            candidates.append((item, full_path, rel_path, os.path.isdir(full_path)))

        if not candidates:
            return set()

        ignored_sources = self._get_git_ignore_sources(
            repo_root,
            [rel_path for _item, _full_path, rel_path, _is_dir in candidates],
        )
        if not ignored_sources:
            return set()

        ignored_items = set()
        for item, full_path, rel_path, is_dir in candidates:
            source_path = ignored_sources.get(rel_path)
            if not source_path:
                continue
            if self._is_oincluded(repo_root, source_path, full_path, is_dir):
                continue
            ignored_items.add(item)
        return ignored_items

    def _get_git_ignore_sources(
        self, repo_root: str, rel_paths: List[str]
    ) -> Dict[str, str]:
        if not rel_paths:
            return {}

        try:
            result = subprocess.run(
                ["git", "-C", repo_root, "check-ignore", "-v", "--stdin"],
                input="\n".join(rel_paths) + "\n",
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError):
            return {}

        if result.returncode not in (0, 1):
            return {}

        sources: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "\t" not in line:
                continue
            source_info, rel_path = line.rsplit("\t", 1)
            parts = source_info.split(":", 2)
            if len(parts) != 3:
                continue
            source_path, _line_number, _pattern = parts
            sources[rel_path.replace("\\", "/")] = source_path.replace("\\", "/")
        return sources

    def _is_oincluded(
        self,
        repo_root: str,
        source_path: str,
        full_path: str,
        is_dir: bool,
    ) -> bool:
        normalized_source = source_path.replace("\\", "/")
        if os.path.basename(normalized_source) != ".gitignore":
            return False

        source_dir_rel = os.path.dirname(normalized_source)
        source_dir = (
            os.path.join(repo_root, source_dir_rel) if source_dir_rel else repo_root
        )
        patterns = self._get_oinclude_patterns(source_dir)
        if not patterns:
            return False

        rel_path = os.path.relpath(full_path, source_dir).replace("\\", "/")
        item_name = os.path.basename(full_path)
        matched = any(
            self._matches_oinclude_pattern(pattern, rel_path, item_name, is_dir)
            for pattern in patterns
        )
        if not matched:
            return False
        return not self._is_reignored_by_nested_gitignore(source_dir, full_path, is_dir)

    def _get_oinclude_patterns(self, source_dir: str) -> List[str]:
        real_source_dir = os.path.realpath(source_dir)
        cached = self._oinclude_cache.get(real_source_dir)
        if cached is not None:
            return cached

        include_path = os.path.join(real_source_dir, ".oinclude")
        patterns = self._read_pattern_file(include_path)
        self._oinclude_cache[real_source_dir] = patterns
        return patterns

    def _matches_oinclude_pattern(
        self,
        pattern: str,
        rel_path: str,
        item_name: str,
        is_dir: bool,
    ) -> bool:
        normalized = pattern.replace("\\", "/").lstrip("/")
        if not normalized:
            return False

        if normalized.endswith("/"):
            base = normalized.rstrip("/")
            return bool(base) and (
                rel_path == base or rel_path.startswith(base + "/")
            )

        if "/" in normalized:
            return fnmatch.fnmatch(rel_path, normalized)

        return fnmatch.fnmatch(item_name, normalized) or fnmatch.fnmatch(
            rel_path, normalized
        )

    def _is_reignored_by_nested_gitignore(
        self, source_dir: str, full_path: str, is_dir: bool
    ) -> bool:
        real_source_dir = os.path.realpath(source_dir)
        target_anchor = (
            os.path.realpath(full_path)
            if is_dir
            else os.path.realpath(os.path.dirname(full_path))
        )

        if target_anchor == real_source_dir:
            return False
        if not target_anchor.startswith(real_source_dir + os.sep):
            return False

        nested_dirs: List[str] = []
        current = target_anchor
        while current.startswith(real_source_dir + os.sep):
            nested_dirs.append(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        for nested_dir in reversed(nested_dirs):
            patterns = self._get_nested_gitignore_patterns(nested_dir)
            if not patterns:
                continue
            rel_path = os.path.relpath(full_path, nested_dir).replace("\\", "/")
            item_name = os.path.basename(full_path)
            if any(
                self._matches_gitignore_pattern(pattern, rel_path, item_name, is_dir)
                for pattern in patterns
            ):
                return True

        return False

    def _get_nested_gitignore_patterns(self, directory: str) -> List[str]:
        real_directory = os.path.realpath(directory)
        cached = self._nested_gitignore_cache.get(real_directory)
        if cached is not None:
            return cached

        patterns = self._read_pattern_file(os.path.join(real_directory, ".gitignore"))
        self._nested_gitignore_cache[real_directory] = patterns
        return patterns

    def _read_pattern_file(self, path: str) -> List[str]:
        patterns: List[str] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    patterns.append(stripped)
        except OSError:
            return []
        return patterns

    def _matches_gitignore_pattern(
        self,
        pattern: str,
        rel_path: str,
        item_name: str,
        is_dir: bool,
    ) -> bool:
        normalized = pattern.replace("\\", "/").lstrip("/")
        if not normalized or normalized.startswith("!"):
            return False

        if normalized.endswith("/"):
            base = normalized.rstrip("/")
            return bool(base) and (
                rel_path == base or rel_path.startswith(base + "/")
            )

        if is_dir and normalized.endswith("/*"):
            base = normalized[:-2]
            if self._matches_gitignore_pathspec(base, rel_path):
                return True

        if "/" in normalized:
            return self._matches_gitignore_pathspec(normalized, rel_path)

        return fnmatch.fnmatch(item_name, normalized)

    def _matches_gitignore_pathspec(self, pattern: str, rel_path: str) -> bool:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if pattern.startswith("**/"):
            suffix = pattern[3:]
            return rel_path == suffix or rel_path.endswith("/" + suffix)
        return False

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
        self._oinclude_cache.clear()
        self._nested_gitignore_cache.clear()

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
