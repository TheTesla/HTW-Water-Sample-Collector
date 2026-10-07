# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""Build the portable Windows app (unpack-and-run) for the wsciot GUI.

Usage (from src/software/wsciot-gui, with Python 3.13):
    python build_portable.py

Produces:
    dist/wsciot-gui/            the portable app folder (run wsciot-gui.exe)
    dist/wsciot-gui-portable.zip  the same folder zipped for distribution

Requires: pip install pyinstaller
The wsciot server package (../wsciot) is bundled UNMODIFIED and executed
via the exe's --server mode (see wsciot_gui/__main__.py).
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


def main():
    if not (SERVER_PKG_DIR / "wsciot" / "__main__.py").exists():
        sys.exit(f"wsciot server package not found at {SERVER_PKG_DIR}")

    # dependencies (paho-mqtt, dotenv) live in the poetry venv - PyInstaller
    # needs its site-packages on the search path to bundle them
    sp = _find_server_venv_site_packages()
    if sp is None:
        sys.exit("no poetry venv with paho-mqtt found - cannot bundle deps")
    print("Bundling dependencies from:", sp)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",                       # GUI app: no console window
        "--name", APP_NAME,
        # make the unmodified server package importable inside the bundle
        "--paths", str(SERVER_PKG_DIR),
        "--paths", str(sp),
        "--hidden-import", "wsciot",
        "--hidden-import", "wsciot.__main__",
        "--hidden-import", "paho.mqtt.client",
        "--hidden-import", "dotenv",
        str(HERE / "wsciot_gui" / "__main__.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=HERE, check=True)

    # sanity: exe exists
    exe = APP_DIR / f"{APP_NAME}.exe"
    if not exe.exists():
        sys.exit(f"build failed: {exe} missing")
    print(f"\nPortable app folder: {APP_DIR}")

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
