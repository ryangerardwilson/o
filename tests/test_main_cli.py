import sys
from pathlib import Path
from types import SimpleNamespace
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

rgw_cli_contract = types.ModuleType("rgw_cli_contract")
rgw_cli_contract.AppSpec = lambda **kwargs: SimpleNamespace(**kwargs)
rgw_cli_contract.resolve_install_script_path = lambda _path: Path("install.sh")


def _run_app(_spec, args, dispatch):
    return dispatch(args)


rgw_cli_contract.run_app = _run_app
sys.modules.setdefault("rgw_cli_contract", rgw_cli_contract)

import main


def test_dispatch_opens_positional_file_detached(monkeypatch, tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")

    opened = []

    monkeypatch.setattr(
        main,
        "_open_file_detached",
        lambda path: opened.append(path) or True,
    )

    class FailOrchestrator:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("orchestrator should not start for file targets")

    monkeypatch.setattr(main, "Orchestrator", FailOrchestrator)

    result = main._dispatch([str(target)])

    assert result == 0
    assert opened == [str(target.resolve())]


def test_open_file_detached_uses_terminal_for_editor(monkeypatch, tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello\n", encoding="utf-8")

    launches = []

    def fake_launch(command, *, cwd=None, env=None):
        launches.append((list(command), cwd))
        return True

    monkeypatch.setattr(main, "_launch_terminal_command", fake_launch)
    monkeypatch.setattr(
        main.config,
        "USER_CONFIG",
        SimpleNamespace(
            get_handler_spec=lambda name: (
                main.config.HandlerSpec(commands=[["nvim"]], is_internal=False)
                if name == "editor"
                else main.config.HandlerSpec(commands=[], is_internal=False)
            )
        ),
        raising=False,
    )

    assert main._open_file_detached(str(target)) is True
    assert launches == [(["nvim", str(target)], str(tmp_path))]
