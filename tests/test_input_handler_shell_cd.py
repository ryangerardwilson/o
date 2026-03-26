import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyNavigator:
    def __init__(self, root: Path, *, shell_cd_enabled: bool):
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
        self.shell_cd_enabled = shell_cd_enabled
        self.requested_shell_cd_path = None

    def build_display_items(self):
        root = self.dir_manager.current_path
        return [("docs", True, str(Path(root) / "docs"), 0)]

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
        if not self.shell_cd_enabled:
            return False
        self.requested_shell_cd_path = path
        return True


def test_n_requests_shell_cd_when_wrapper_is_enabled(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    nav = DummyNavigator(tmp_path, shell_cd_enabled=True)
    handler = InputHandler(nav)

    handled = handler.handle_key(None, ord("n"))

    assert handled is True
    assert nav.requested_shell_cd_path == str(tmp_path)


def test_n_guides_user_when_shell_wrapper_is_missing(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    nav = DummyNavigator(tmp_path, shell_cd_enabled=False)
    handler = InputHandler(nav)

    handled = handler.handle_key(None, ord("n"))

    assert handled is False
    assert nav.requested_shell_cd_path is None
    assert "Shell cd hook missing" in nav.status_message
    assert "70-integrations.sh" in nav.status_message
