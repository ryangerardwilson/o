import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyNavigator:
    def __init__(self, root: Path, display_items):
        self.dir_manager = SimpleNamespace(current_path=str(root), filter_pattern="")
        self.renderer = SimpleNamespace(stdscr=None)
        self.file_actions = SimpleNamespace()
        self.clipboard = SimpleNamespace(has_entries=False, entry_count=0)
        self.marked_items: set[str] = set()
        self.expanded_nodes: set[str] = set()
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
        self.command_popup_lock = SimpleNamespace(
            __enter__=lambda self: self,
            __exit__=lambda self, exc_type, exc, tb: False,
        )
        self.picker_options = None
        self.requested_shell_cd_path = None
        self._display_items = list(display_items)

    def build_display_items(self):
        return list(self._display_items)

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

    def request_shell_cd(self, path):
        self.requested_shell_cd_path = path
        return True


def test_n_uses_current_directory_context_for_top_level_rows(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    display_items = [("docs", True, str(docs), 0)]
    nav = DummyNavigator(tmp_path, display_items)
    handler = InputHandler(nav)

    handled = handler.handle_key(None, ord("n"))

    assert handled is True
    assert nav.requested_shell_cd_path == str(tmp_path)


def test_n_uses_expanded_directory_context_inside_inline_subtree(tmp_path):
    parent = tmp_path / "docs"
    parent.mkdir()
    file_path = parent / "note.txt"
    file_path.write_text("hi\n", encoding="utf-8")
    display_items = [
        ("docs", True, str(parent), 0),
        ("note.txt", False, str(file_path), 1),
    ]
    nav = DummyNavigator(tmp_path, display_items)
    nav.expanded_nodes.add(str(parent))
    nav.browser_selected = 1
    handler = InputHandler(nav)

    handled = handler.handle_key(None, ord("n"))

    assert handled is True
    assert nav.requested_shell_cd_path == str(parent)
