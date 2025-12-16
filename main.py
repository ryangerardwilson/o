# ~/Apps/vios/main.py
#!/usr/bin/env python3
import curses
import os
import sys

# Updated import to reflect the new split
from modules.core_navigator import FileNavigator


def main(stdscr):
    # Start in the current working directory
    start_path = os.getcwd()
    
    navigator = FileNavigator(start_path)
    
    try:
        navigator.run(stdscr)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C (though curses.wrapper already handles most cleanup)
        sys.exit(0)


if __name__ == "__main__":
    # curses.wrapper ensures proper initialization and restoration of the terminal
    curses.wrapper(main)
