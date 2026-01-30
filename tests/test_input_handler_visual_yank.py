import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyClipboard:
    def __init__(self):
        self.yanked = []
        self.has_entries = False
        self.entry_count = 0

    def yank_multiple(self, entries, cut=False):
        self.yanked.append((tuple(entries), cut))
        self.has_entries = True
        self.entry_count = len(entries)


class DummyDirManager:
    def __init__(self, current_path):
        self.current_path = current_path
        self.filter_pattern = ""

    def get_filtered_items(self):
        return []


def make_handler(entries, marked_paths, current_path):
    clipboard = DummyClipboard()
    dir_manager = DummyDirManager(current_path)

    nav = SimpleNamespace(
        dir_manager=dir_manager,
        clipboard=clipboard,
        marked_items=set(marked_paths),
        expanded_nodes=set(),
        visual_mode=False,
        get_visual_indices=lambda total: [],
        exit_visual_mode=lambda **kwargs: None,
        status_message="",
        need_redraw=False,
        update_visual_active=lambda idx: None,
        show_help=False,
        command_popup_visible=False,
        in_filter_mode=False,
        layout_mode="list",
        browser_selected=0,
        list_offset=0,
        notify_directory_changed=lambda *paths: None,
    )

    handler = InputHandler(nav)

    def build_display_items():
        return entries

    nav.build_display_items = build_display_items
    return handler, nav


def test_single_y_yanks_marked_items(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")
    dir_path = tmp_path / "dir"
    dir_path.mkdir()

    entries = [
        ("file.txt", False, str(file_path), 0),
        ("dir", True, str(dir_path), 0),
    ]

    handler, nav = make_handler(entries, {str(file_path), str(dir_path)}, str(tmp_path))

    handler.handle_key(None, ord("y"))

    assert nav.clipboard.yanked, "Clipboard should record a yank"
    yanked_entries, cut = nav.clipboard.yanked[-1]
    assert cut is False
    assert {path for path, *_ in yanked_entries} == {
        str(file_path),
        str(dir_path),
    }
    assert nav.marked_items == set()
    assert handler.pending_operator is None


def test_single_y_without_marks_sets_operator(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")

    entries = [("file.txt", False, str(file_path), 0)]

    handler, nav = make_handler(entries, set(), str(tmp_path))

    handler.handle_key(None, ord("y"))

    assert handler.pending_operator == "y"
    assert nav.clipboard.yanked == []
