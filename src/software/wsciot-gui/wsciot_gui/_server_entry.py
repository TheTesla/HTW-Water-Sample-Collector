# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""Server entry point for the portable wsciot app.

Built into ``wsciot-server.exe`` (see build_portable.py). Runs the
ORIGINAL, unmodified wsciot server module. This executable contains no
GUI code path at all - the GUI (wsciot-gui.exe) starts it as a child.
"""
import runpy

if __name__ == "__main__":
    runpy.run_module("wsciot", run_name="__main__")
