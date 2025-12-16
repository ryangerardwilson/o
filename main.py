#!/usr/bin/env python3
import curses
import os
import sys
from modules.navigator import FileNavigator

def main(stdscr):
    start_path = os.getcwd()
    navigator = FileNavigator(start_path)
    try:
        navigator.run(stdscr)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    # Run with curses.wrapper to handle terminal properly
    curses.wrapper(main)
