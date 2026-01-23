import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config


def test_workspace_external_empty_command_list_is_treated_as_no_preference(tmp_path):
    internal_dir = tmp_path / "workspace"
    internal_dir.mkdir()

    raw = {
        "3": {
            "internal": str(internal_dir),
            "external": [[]],
        }
    }

    shortcuts, warnings = config._normalize_workspace_shortcuts(raw)

    assert warnings == []
    assert "3" in shortcuts

    entry = shortcuts["3"]
    assert entry["internal_path"] == os.path.realpath(internal_dir)
    assert "external_commands" not in entry


def test_workspace_external_invalid_entries_still_warn(tmp_path):
    internal_dir = tmp_path / "workspace"
    internal_dir.mkdir()

    raw = {
        "3": {
            "internal": str(internal_dir),
            "external": [[""], 5],
        }
    }

    shortcuts, warnings = config._normalize_workspace_shortcuts(raw)

    assert any(
        "workspace_shortcuts '3' external ignored (no valid commands)" in warning
        for warning in warnings
    )

    # Internal path should still be present despite the invalid external commands
    entry = shortcuts["3"]
    assert entry["internal_path"] == os.path.realpath(internal_dir)
