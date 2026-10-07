# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""Entry point of the wsciot GUI launcher.

Normal mode:  python -m wsciot_gui        (or wsciot-gui.exe)
Server mode:  python -m wsciot_gui --server
              (or wsciot-gui.exe --server, used by the portable app to
              launch the bundled original wsciot server as a child
              process; the server code itself stays unmodified)
"""
import sys


def main():
    if "--server" in sys.argv:
        import runpy
        # run the ORIGINAL, unmodified wsciot server module
        runpy.run_module("wsciot", run_name="__main__")
        return
    from wsciot_gui.gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
