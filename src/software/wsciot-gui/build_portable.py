# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""Build the portable Windows app (unpack-and-run) for the wsciot GUI.

Usage (from src/software/wsciot-gui, with Python 3.13):
    python build_portable.py

Produces TWO executables in one folder (dist/wsciot-gui):
    wsciot-gui.exe     the GUI (tkinter, onedir bundle)
    wsciot-server.exe  the server (runs the ORIGINAL, unmodified wsciot
                       server module; one-file bundle, no GUI code path)

The GUI starts wsciot-server.exe as a child. Two separate programs mean
the server process can never open a GUI window, and the process list
shows clearly which is which.

Also written:
    dist/wsciot-gui-portable.zip   the folder zipped for distribution

Requires: pip install pyinstaller
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER_PKG_DIR = HERE.parent / "wsciot"
DIST = HERE / "dist"
APP_NAME = "wsciot-gui"
SERVER_NAME = "wsciot-server"
APP_DIR = DIST / APP_NAME
ZIP_PATH = DIST / f"{APP_NAME}-portable.zip"


def _find_server_venv_site_packages():
    """Site-packages of a poetry venv that has paho+dotenv (for bundling)."""
    venv_root = Path.home() / "AppData" / "Local" / "pypoetry" / "Cache" / "virtualenvs"
    if not venv_root.is_dir():
        return None
    for venv in sorted(venv_root.glob("wsciot-*"), reverse=True):
        sp = venv / "Lib" / "site-packages"
        if (sp / "paho").is_dir():
            return sp
    return None


def _pyinstaller(args):
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean"] + args
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=HERE, check=True)


def main():
    if not (SERVER_PKG_DIR / "wsciot" / "__main__.py").exists():
        sys.exit(f"wsciot server package not found at {SERVER_PKG_DIR}")

    # dependencies (paho-mqtt, dotenv) live in the poetry venv - PyInstaller
    # needs its site-packages on the search path to bundle them
    sp = _find_server_venv_site_packages()
    if sp is None:
        sys.exit("no poetry venv with paho-mqtt found - cannot bundle deps")
    print("Bundling dependencies from:", sp)

    common = ["--noconsole",
              "--paths", str(SERVER_PKG_DIR),
              "--paths", str(sp),
              "--hidden-import", "wsciot",
              "--hidden-import", "wsciot.__main__",
              "--hidden-import", "paho.mqtt.client",
              "--hidden-import", "dotenv"]

    # 1) GUI app (onedir folder bundle)
    _pyinstaller(common + ["--name", APP_NAME,
                           str(HERE / "wsciot_gui" / "__main__.py")])
    gui_exe = APP_DIR / f"{APP_NAME}.exe"
    if not gui_exe.exists():
        sys.exit(f"build failed: {gui_exe} missing")

    # 2) server app (single-file exe; onefile output lands in DIST root)
    _pyinstaller(common + ["--onefile", "--name", SERVER_NAME,
                           str(HERE / "wsciot_gui" / "_server_entry.py")])
    server_src = DIST / f"{SERVER_NAME}.exe"
    if not server_src.exists():
        sys.exit(f"build failed: {server_src} missing")

    # move the server exe next to the GUI exe
    server_exe = APP_DIR / f"{SERVER_NAME}.exe"
    shutil.move(str(server_src), server_exe)
    print(f"\nPortable app folder: {APP_DIR}")
    print(f"  {gui_exe.name}     (GUI)")
    print(f"  {server_exe.name}  (server, started by the GUI)")

    # distribution zip
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(APP_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(APP_DIR.parent))
    size_mb = ZIP_PATH.stat().st_size / 1e6
    print(f"Distribution zip:   {ZIP_PATH} ({size_mb:.1f} MB)")
    print("\nUsers: unpack the zip anywhere and run wsciot-gui.exe")


if __name__ == "__main__":
    main()
