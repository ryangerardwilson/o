import os
import sys
from pathlib import Path
from types import SimpleNamespace
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

rgw_cli_contract = types.ModuleType("rgw_cli_contract")
rgw_cli_contract.AppSpec = lambda **kwargs: SimpleNamespace(**kwargs)
rgw_cli_contract.resolve_install_script_path = lambda _path: Path("install.sh")
rgw_cli_contract.run_app = lambda _spec, args, dispatch: dispatch(args)
sys.modules.setdefault("rgw_cli_contract", rgw_cli_contract)

import main


def test_write_shell_cd_request_writes_realpath(tmp_path, monkeypatch):
    handoff = tmp_path / "handoff.txt"
    target = tmp_path / "nested" / ".."
    target.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv(main.SHELL_CD_ENV, str(handoff))

    assert main._write_shell_cd_request(str(target)) is True
    assert handoff.read_text(encoding="utf-8") == str(target.resolve()) + "\n"


def test_dispatch_writes_shell_cd_request_on_shell_cd_exit(tmp_path, monkeypatch):
    handoff = tmp_path / "handoff.txt"
    target = tmp_path / "docs"
    target.mkdir()

    class FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            self.navigator = SimpleNamespace(
                exit_reason="shell_cd",
                selection_result=[str(target)],
            )

        def run(self):
            return None

    monkeypatch.setenv(main.SHELL_CD_ENV, str(handoff))
    monkeypatch.setattr(main, "Orchestrator", FakeOrchestrator)

    result = main._dispatch([])

    assert result == 0
    assert handoff.read_text(encoding="utf-8") == str(target.resolve()) + "\n"
