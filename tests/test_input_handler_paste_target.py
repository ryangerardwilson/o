import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_handler import InputHandler


class DummyNavigator:
    def __init__(self, current_path: str):
        self.dir_manager = SimpleNamespace(current_path=current_path)
        self.expanded_nodes: set[str] = set()


def make_handler(current_path: str = "/tmp/root"):
    nav = DummyNavigator(current_path)
    handler = InputHandler(nav)
    return handler, nav


def test_paste_targets_expanded_directory_when_on_contents():
    handler, nav = make_handler()
    expanded_dir = os.path.join(nav.dir_manager.current_path, "alpha")
    nav.expanded_nodes.add(expanded_dir)

    items = [
        ("alpha", True, expanded_dir, 0),
        ("file.txt", False, os.path.join(expanded_dir, "file.txt"), 1),
    ]

    context_path, scope_range, context_index = handler._compute_context_scope(items, 1)
    target = handler._determine_target_directory(
        items[1][2],
        False,
        selected_index=1,
        context_path=context_path,
        context_index=context_index,
        scope_range=scope_range,
    )

    assert target == os.path.realpath(expanded_dir)


def test_paste_targets_current_directory_when_on_directory_header():
    handler, nav = make_handler()
    expanded_dir = os.path.join(nav.dir_manager.current_path, "alpha")
    nav.expanded_nodes.add(expanded_dir)

    items = [
        ("alpha", True, expanded_dir, 0),
        ("file.txt", False, os.path.join(expanded_dir, "file.txt"), 1),
    ]

    context_path, scope_range, context_index = handler._compute_context_scope(items, 0)
    target = handler._determine_target_directory(
        items[0][2],
        True,
        selected_index=0,
        context_path=context_path,
        context_index=context_index,
        scope_range=scope_range,
    )

    assert target == nav.dir_manager.current_path


def test_paste_targets_current_directory_when_directory_not_expanded():
    handler, nav = make_handler()
    collapsed_dir = os.path.join(nav.dir_manager.current_path, "beta")

    items = [("beta", True, collapsed_dir, 0)]

    context_path, scope_range, context_index = handler._compute_context_scope(items, 0)
    target = handler._determine_target_directory(
        items[0][2],
        True,
        selected_index=0,
        context_path=context_path,
        context_index=context_index,
        scope_range=scope_range,
    )

    assert target == nav.dir_manager.current_path


def test_paste_targets_nested_context_directory():
    handler, nav = make_handler()
    level_one = os.path.join(nav.dir_manager.current_path, "alpha")
    level_two = os.path.join(level_one, "bravo")
    nav.expanded_nodes.update({level_one, level_two})

    items = [
        ("alpha", True, level_one, 0),
        ("bravo", True, level_two, 1),
        ("note.md", False, os.path.join(level_two, "note.md"), 2),
    ]

    context_path, scope_range, context_index = handler._compute_context_scope(items, 2)
    target = handler._determine_target_directory(
        items[2][2],
        False,
        selected_index=2,
        context_path=context_path,
        context_index=context_index,
        scope_range=scope_range,
    )

    assert target == os.path.realpath(level_two)
