# ~/Apps/vios/modules/command_processor.py

import curses
import os
import subprocess


class CommandProcessor:
    ALLOWED_COMMANDS = {"mkdir", "mv", "cp", "rm", "vim", "v", "cd", "c", "r"}

    def __init__(self, directory_manager, open_vim_callback):
        self.directory_manager = directory_manager
        self.open_vim_callback = open_vim_callback

    def is_command_allowed(self, cmd_line: str) -> bool:
        if not cmd_line.strip():
            return False
        parts = cmd_line.split(";")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            words = part.split()
            base_cmd = words[0] if words else ""
            if base_cmd == "v":
                base_cmd = "vim"
            if base_cmd not in self.ALLOWED_COMMANDS:
                return False
        return True

    def run_shell_command(self, command: str):
        if not self.is_command_allowed(command):
            curses.flash()
            return

        stripped = command.strip()
        current_dir = self.directory_manager.current_path

        # Handle cd / c
        if stripped.startswith(("cd ", "c ")):
            target = stripped.split(maxsplit=1)[1] if " " in stripped else "~"
            new_path = os.path.expanduser(target)
            if not os.path.isabs(new_path):
                new_path = os.path.join(current_dir, new_path)
            if self.directory_manager.change_directory(new_path):
                return
            else:
                curses.flash()
                return

        # Handle vim / v  — THIS IS THE FIXED PART
        if stripped.startswith(("vim ", "v ")):
            # Extract the filename part after vim/v
            target = stripped.split(maxsplit=1)[1] if " " in stripped else ""

            # Expand ~ and make path absolute relative to current navigator dir
            target_expanded = os.path.expanduser(target)
            if not os.path.isabs(target_expanded):
                target_expanded = os.path.join(current_dir, target_expanded)

            # Normalize the path (resolve .., etc.)
            full_path = os.path.normpath(target_expanded)

            # Always pass the full path to Vim, and force Vim to cd to current_dir
            # This ensures new files are created in the right place
            self.open_vim_callback(full_path)
            return

        # All other allowed shell commands (mkdir, cp, mv, rm, etc.)
        home = os.path.expanduser("~")
        bashrc = os.path.join(home, ".bashrc")
        full_cmd = f"source {bashrc} >/dev/null 2>&1 && {command} >/dev/null 2>&1"

        subprocess.Popen(
            full_cmd,
            shell=True,
            cwd=current_dir,
            executable="/bin/bash",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
