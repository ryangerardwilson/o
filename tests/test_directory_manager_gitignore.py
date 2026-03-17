import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from directory_manager import DirectoryManager


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(
    not shutil.which("git"), reason="git is required for gitignore integration tests"
)
def test_directory_manager_hides_gitignored_entries(tmp_path):
    repo = tmp_path
    _git(repo, "init")
    (repo / ".gitignore").write_text("build/\n*.apk\n", encoding="utf-8")
    (repo / "build").mkdir()
    (repo / "build" / "generated.txt").write_text("ignored\n", encoding="utf-8")
    (repo / "app.apk").write_text("ignored\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (repo / "README.md").write_text("visible\n", encoding="utf-8")

    manager = DirectoryManager(str(repo))

    assert [name for name, _is_dir in manager.get_items()] == ["src", "README.md"]


@pytest.mark.skipif(
    not shutil.which("git"), reason="git is required for gitignore integration tests"
)
def test_directory_manager_applies_parent_repo_gitignore_from_nested_directory(tmp_path):
    repo = tmp_path
    nested = repo / "apps" / "frontend" / "android"
    nested.mkdir(parents=True)

    _git(repo, "init")
    (repo / ".gitignore").write_text("*.apk\nbuild/\n", encoding="utf-8")
    (nested / "build").mkdir()
    (nested / "build" / "generated.txt").write_text("ignored\n", encoding="utf-8")
    (nested / "debug.apk").write_text("ignored\n", encoding="utf-8")
    (nested / "src").mkdir()
    (nested / "README.md").write_text("visible\n", encoding="utf-8")

    manager = DirectoryManager(str(nested))

    assert [name for name, _is_dir in manager.get_items()] == ["src", "README.md"]
