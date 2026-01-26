from core_navigator import FileNavigator
from keys import KEY_CTRL_J, KEY_ENTER_CARRIAGE


def test_enter_toggles_layout_mode(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    nav.enter_list_mode()
    original_layout = nav.layout_mode

    handler.handle_key(None, KEY_ENTER_CARRIAGE)
    assert nav.layout_mode != original_layout

    handler.handle_key(None, KEY_ENTER_CARRIAGE)
    assert nav.layout_mode == original_layout


def test_ctrl_j_does_not_toggle_layout(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    nav.enter_list_mode()
    original_layout = nav.layout_mode
    handler.handle_key(None, KEY_CTRL_J)

    # Ctrl+J should preserve the current layout and remain in list mode.
    assert nav.layout_mode == original_layout


def test_filter_mode_ctrl_j_does_not_submit(tmp_path):
    nav = FileNavigator(str(tmp_path))
    handler = nav.input_handler

    nav.enter_list_mode()
    handler.in_filter_mode = True
    nav.dir_manager.filter_pattern = "/notes"

    handler.handle_key(None, KEY_CTRL_J)
    assert handler.in_filter_mode is True
    assert nav.dir_manager.filter_pattern == "/notes"

    handler.handle_key(None, KEY_ENTER_CARRIAGE)
    assert handler.in_filter_mode is False
    assert nav.dir_manager.filter_pattern == "notes"
