import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from directory_manager import DirectoryManager
from input_handler import InputHandler


def _create_file(path: Path, mtime: float) -> Path:
    path.write_text(path.name)
    os.utime(path, (mtime, mtime))
    return path


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyNavigator:
    def __init__(self, root: Path):
        self.dir_manager = DirectoryManager(str(root))
        self.expanded_nodes: set[str] = set()
        self.marked_items: set[str] = set()
        self.visual_mode = False
        self.status_message = ""
        self.need_redraw = False
        self.browser_selected = 0
        self.layout_mode = "list"
        self.leader_sequence = ""
        self.command_popup_visible = False
        self.show_help = False
        self.command_mode = False
        self.command_history: list[str] = []
        self.command_history_index = None
        self.command_buffer = ""
        self.command_popup_lock = DummyLock()
        self.clipboard = type(
            "DummyClipboard",
            (),
            {"has_entries": False, "entry_count": 0},
        )()

    def build_display_items(self):
        items = []
        root = self.dir_manager.current_path
        for name, is_dir in self.dir_manager.get_filtered_items():
            items.append((name, is_dir, os.path.join(root, name), 0))
        return items

    def update_visual_active(self, _idx):
        pass

    def exit_visual_mode(self, **_kwargs):
        self.visual_mode = False

    def collapse_expansions_under(self, _path):
        pass

    def reset_to_home(self):
        pass

    def go_history_back(self):
        return False

    def go_history_forward(self):
        return False

    def enter_matrix_mode(self):
        self.layout_mode = "matrix"

    def enter_list_mode(self):
        self.layout_mode = "list"

    def change_directory(self, _path):
        return False

    def remember_matrix_position(self):
        pass

    def discard_matrix_position(self, _path):
        pass

    def open_file(self, _path):
        pass

    def open_terminal(self):
        pass


def _visible_names(nav: DummyNavigator) -> list[str]:
    return [name for name, _is_dir, _path, _depth in nav.build_display_items()]


def _press(handler: InputHandler, sequence: str) -> None:
    for ch in sequence:
        handler.handle_key(None, ord(ch))


def test_directory_manager_reorders_cached_items_after_global_sort_change(tmp_path):
    now = time.time()
    _create_file(tmp_path / "aaa_new.txt", now)
    _create_file(tmp_path / "zzz_old.txt", now - 1000)

    manager = DirectoryManager(str(tmp_path))

    assert [name for name, _is_dir in manager.get_items()] == [
        "aaa_new.txt",
        "zzz_old.txt",
    ]

    manager.set_sort_mode("mtime_asc")
    assert [name for name, _is_dir in manager.get_items()] == [
        "zzz_old.txt",
        "aaa_new.txt",
    ]

    manager.set_sort_mode("mtime_desc")
    assert [name for name, _is_dir in manager.get_items()] == [
        "aaa_new.txt",
        "zzz_old.txt",
    ]


def test_leader_sort_commands_refresh_visible_order_immediately(tmp_path):
    now = time.time()
    _create_file(tmp_path / "aaa_new.txt", now)
    _create_file(tmp_path / "zzz_old.txt", now - 1000)

    nav = DummyNavigator(tmp_path)
    handler = InputHandler(nav)

    assert _visible_names(nav) == ["aaa_new.txt", "zzz_old.txt"]

    _press(handler, ",sma")
    assert _visible_names(nav) == ["zzz_old.txt", "aaa_new.txt"]
    assert nav.status_message == "Sort: Modified ↑"

    _press(handler, ",smd")
    assert _visible_names(nav) == ["aaa_new.txt", "zzz_old.txt"]
    assert nav.status_message == "Sort: Modified ↓"
