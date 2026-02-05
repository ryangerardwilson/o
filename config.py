import json
import os
import shlex
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class ExecutorsSpec:
    python: List[str] = field(default_factory=list)
    shell: List[str] = field(default_factory=list)

    def get(self, name: str) -> List[str]:
        if name == "python":
            return list(self.python)
        if name == "shell":
            return list(self.shell)
        return []


@dataclass
class UserConfig:
    matrix_mode: bool = False
    handlers: Dict[str, "HandlerSpec"] = field(default_factory=dict)
    executors: ExecutorsSpec = field(default_factory=ExecutorsSpec)
    warnings: List[str] = field(default_factory=list)

    def get_handler_commands(self, name: str) -> List[List[str]]:
        return self.get_handler_spec(name).commands

    def get_handler_spec(self, name: str) -> "HandlerSpec":
        spec = self.handlers.get(name)
        if spec is None:
            return HandlerSpec(commands=[], is_internal=False)
        return spec

    def get_executor(self, name: str) -> List[str]:
        return self.executors.get(name)


@dataclass
class HandlerSpec:
    commands: List[List[str]] = field(default_factory=list)
    is_internal: bool = False


def _config_path() -> str:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if not xdg_config:
        xdg_config = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(xdg_config, "o", "config.json")


def _normalize_command(entry) -> List[str]:
    if isinstance(entry, str):
        return shlex.split(entry) if entry.strip() else []
    if isinstance(entry, list):
        if all(isinstance(token, str) for token in entry):
            return [token for token in entry if token]
    return []


def _normalize_handlers(raw_handlers) -> Dict[str, HandlerSpec]:
    handlers: Dict[str, HandlerSpec] = {}

    if not isinstance(raw_handlers, dict):
        return handlers

    for raw_key, raw_value in raw_handlers.items():
        key = raw_key.strip() if isinstance(raw_key, str) else None
        if not key:
            continue

        commands: List[List[str]] = []
        is_internal = False

        if isinstance(raw_value, dict):
            commands_value = raw_value.get("commands")
            if commands_value is None and "command" in raw_value:
                commands_value = raw_value.get("command")
            commands = _normalize_handler_commands(commands_value)
            is_internal = bool(raw_value.get("is_internal"))
        else:
            commands = _normalize_handler_commands(raw_value)
            is_internal = False

        if not commands:
            continue

        handlers[key] = HandlerSpec(commands=commands, is_internal=is_internal)

    return handlers


def _normalize_handler_commands(raw_value) -> List[List[str]]:
    commands: List[List[str]] = []

    if isinstance(raw_value, list):
        # If the value looks like a single command expressed as a list of tokens
        # (e.g. ["vim", "{file}"]), treat it as one entry. Otherwise iterate.
        if raw_value and all(isinstance(entry, str) for entry in raw_value):
            cmd = _normalize_command(raw_value)
            if cmd:
                commands.append(cmd)
        else:
            for entry in raw_value:
                cmd = _normalize_command(entry)
                if cmd:
                    commands.append(cmd)
    else:
        cmd = _normalize_command(raw_value)
        if cmd:
            commands.append(cmd)

    return commands


def _default_python_executor() -> List[str]:
    candidates: List[str] = []

    exe = sys.executable
    if exe:
        exe_path = os.path.realpath(exe)
        if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
            candidates.append(exe_path)

    for name in ("python3", "python"):
        path = shutil.which(name)
        if path and path not in candidates:
            candidates.append(path)

    if not candidates:
        return []

    # Use the first candidate and split into command tokens
    return _normalize_command(candidates[0])


def _default_shell_executor() -> List[str]:
    for command in (["/bin/bash", "-lc"], ["/bin/sh", "-c"]):
        shell_path = command[0]
        if shutil.which(shell_path):
            return list(command)
    return []


def _normalize_executors(raw_value) -> Tuple[ExecutorsSpec, List[str]]:
    warnings: List[str] = []
    python_cmd: List[str] = []
    shell_cmd: List[str] = []

    if isinstance(raw_value, dict):
        if "python" in raw_value:
            python_cmd = _normalize_command(raw_value.get("python"))
            if not python_cmd:
                warnings.append("Invalid python executor configuration; falling back to defaults")
        if "shell" in raw_value:
            shell_cmd = _normalize_command(raw_value.get("shell"))
            if not shell_cmd:
                warnings.append("Invalid shell executor configuration; falling back to defaults")

    if not python_cmd:
        python_cmd = _default_python_executor()
        if not python_cmd:
            warnings.append("No python executor available; Python execution disabled")

    if not shell_cmd:
        shell_cmd = _default_shell_executor()
        if not shell_cmd:
            warnings.append("No shell executor available; shell execution disabled")

    return ExecutorsSpec(python=python_cmd, shell=shell_cmd), warnings


def load_user_config() -> UserConfig:
    path = _config_path()
    data = {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        pass
    except Exception:
        data = {}

    matrix_mode = data.get("matrix_mode")
    if not isinstance(matrix_mode, bool):
        matrix_mode = False

    warnings: List[str] = []

    handlers = _normalize_handlers(data.get("handlers", {}))
    executors, executor_warnings = _normalize_executors(data.get("executors", {}))
    warnings.extend(executor_warnings)

    deprecated_keys = (
        "file_shortcuts",
        "dir_shortcuts",
        "workspace_shortcuts",
    )
    for key in deprecated_keys:
        if key in data:
            warnings.append(f"{key} is no longer supported and was ignored")

    if "browser_setup" in data:
        warnings.append("browser_setup is no longer supported and was ignored")

    if "browser_shortcuts" in data:
        warnings.append("browser_shortcuts is no longer supported and was ignored")

    return UserConfig(
        matrix_mode=matrix_mode,
        handlers=handlers,
        executors=executors,
        warnings=warnings,
    )


USER_CONFIG = load_user_config()


def get_config_path() -> str:
    return _config_path()
