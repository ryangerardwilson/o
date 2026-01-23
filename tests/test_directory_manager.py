import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from directory_manager import DirectoryManager


def test_toggle_hidden_refreshes_cached_listings(tmp_path):
    (tmp_path / "visible.txt").write_text("visible")
    (tmp_path / ".hidden.txt").write_text("hidden")

    manager = DirectoryManager(str(tmp_path))

    # Prime the cache while hidden files are disabled
    initial_names = {name for name, _ in manager.get_items()}
    assert ".hidden.txt" not in initial_names

    # Toggling hidden files should clear the cache and include hidden entries
    manager.toggle_hidden()
    names_with_hidden = {name for name, _ in manager.get_items()}
    assert ".hidden.txt" in names_with_hidden

    # Toggling again should hide the entries once more
    manager.toggle_hidden()
    names_without_hidden = {name for name, _ in manager.get_items()}
    assert ".hidden.txt" not in names_without_hidden
