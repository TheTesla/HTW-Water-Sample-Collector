# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""Helpers for the wsciot GUI launcher.

Keeps all non-GUI logic in one place: locating the wsciot server package,
reading/writing the ``.env`` file, and starting/stopping/monitoring the
original wsciot server as a detached background process.

The server itself is NOT modified. It is started with the directory
containing the ``.env`` file as working directory, exactly like a manual
``poetry run python3 wsciot`` from the documentation.
"""

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

# Keys of the .env file, in display order. ``secret=True`` fields are
# displayed masked in the GUI. Defaults match the original server program.
ENV_FIELDS = [
    ("TTN_APP_ID", "TTN App ID", False),
    ("TTN_ACCESS_KEY", "TTN Access Key", True),
    ("MQTT_BROKER", "MQTT Broker", False),
    ("MQTT_PORT", "MQTT Port", False),
    ("MQTT_TOPIC", "MQTT Topic", False),
    ("EMAIL_FROM", "E-Mail Absender (From)", False),
    ("EMAIL_TO", "E-Mail Empfaenger (To)", False),
    ("SMTP_SERVER", "SMTP Server", False),
    ("SMTP_PORT", "SMTP Port", False),
    ("SMTP_USER", "SMTP Benutzer", False),
    ("SMTP_PASSWORD", "SMTP Passwort", True),
]

SERVER_PACKAGE = "wsciot"
# Server's built-in port defaults (matches creds.get("MQTT_PORT", 1883) etc.
# in the original server). Ports at these values are omitted from the .env
# (a string port line crashes the original server) and shown pre-filled in
# the GUI.
PORT_DEFAULTS = {"MQTT_PORT": "1883", "SMTP_PORT": "587"}


def is_frozen():
    """True when running as a PyInstaller bundle (portable app)."""
    return getattr(sys, "frozen", False)


def default_env_path():
    """The .env file of the wsciot server, derived from the server directory.

    Portable app: the .env sits next to the executable.
    Source run: derived from the server package location (never a
    machine-specific absolute path).
    """
    if is_frozen():
        return Path(sys.executable).parent / ".env"
    server_dir = find_server_dir()
    if server_dir is not None:
        return server_dir / ".env"
    return Path.cwd() / SERVER_PACKAGE / ".env"


def find_server_dir():
    """Return the directory containing the wsciot server package.

    Portable app: the executable's own directory (holds .env and the
    server log; the server code is bundled inside the executable).
    """
    if is_frozen():
        return Path(sys.executable).parent
    candidates = []
    # gui lives in <server_root>/wsciot-gui/wsciot_gui/logic.py ->
    # server root is two levels up (src/software)
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / SERVER_PACKAGE)           # src/software/wsciot
    candidates.append(here.parent.parent / SERVER_PACKAGE)    # fallback layout
    candidates.append(Path.cwd() / SERVER_PACKAGE)
    for cand in candidates:
        if (cand / SERVER_PACKAGE / "__main__.py").exists():
            return cand
    return None


def find_python_and_launch_cmd(server_dir):
    """Return the command used to launch the wsciot server.

    Portable app: launch this executable itself with the --server flag
    (it then runs the bundled original wsciot server code).
    Source run: prefer a Poetry virtualenv that has the wsciot package
    installed (paho-mqtt present); fall back to plain ``python -m wsciot``.
    """
    if is_frozen():
        return [sys.executable, "--server"], Path(sys.executable)
    server_dir = Path(server_dir)
    pythons = []

    # 1) Poetry virtualenvs of this project (name starts with "wsciot-")
    venv_root = Path(os.environ.get("POETRY_VIRTUALENVS_PATH",
                                    Path.home() / "AppData" / "Local" / "pypoetry" / "Cache" / "virtualenvs"))
    if venv_root.is_dir():
        for venv in sorted(venv_root.glob("wsciot-*"), reverse=True):
            py = venv / "Scripts" / "python.exe"
            if not py.exists():
                py = venv / "bin" / "python"
            if py.exists():
                pythons.append(py)

    # 2) local .venv next to the server
    for py in (server_dir / ".venv" / "Scripts" / "python.exe",
               server_dir / ".venv" / "bin" / "python"):
        if py.exists():
            pythons.append(py)

    # 3) plain system interpreters as last resort
    pythons.append(Path(sys.executable))

    for py in pythons:
        try:
            r = subprocess.run(
                [str(py), "-c", "import paho.mqtt.client, dotenv"],
                capture_output=True, timeout=30,
            )
            if r.returncode == 0:
                return [str(py), "-m", SERVER_PACKAGE], py
        except (OSError, subprocess.TimeoutExpired):
            continue
    return [str(sys.executable), "-m", SERVER_PACKAGE], sys.executable


def read_env(path):
    """Read the .env file into a dict (raw lines preserved separately)."""
    env = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def write_env(path, values):
    """Write the given values to the .env file (quoted, UTF-8).

    The original server reads port values via ``creds.get("MQTT_PORT",
    1883)`` and passes them straight to ``client.connect``, which requires
    an ``int``. python-dotenv always yields strings, so a port line in the
    .env crashes the original server. Ports are therefore only written
    when they differ from the server's built-in defaults (empty field or
    default value -> line omitted, server default applies).

    A ``{TTN_APP_ID}`` placeholder inside MQTT_TOPIC is resolved here,
    because the original server only builds that default topic when the
    MQTT_TOPIC line is absent - it never substitutes placeholders itself.
    """
    port_defaults = PORT_DEFAULTS
    ttn_app_id = values.get("TTN_APP_ID", "").strip()
    lines = ["# Configuration for the wsciot msg forwarding server",
             "# edited by the wsciot GUI launcher", ""]
    for key, _label, _secret in ENV_FIELDS:
        val = values.get(key, "").strip()
        if key in port_defaults and (not val or val == port_defaults[key]):
            continue
        if key == "MQTT_TOPIC" and val:
            val = val.replace("{TTN_APP_ID}", ttn_app_id)
        lines.append(f'{key} = "{val}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def start_server(server_dir, python_exe, log_path):
    """Start the wsciot server detached; returns the Popen handle.

    On Windows, CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS fully
    detaches the server from this GUI so it survives GUI exit.
    """
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [str(python_exe), "-m", SERVER_PACKAGE],
        cwd=str(server_dir),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    # Detach from our side, so the child is NOT killed when this process ends
    try:
        proc.poll()
    finally:
        pass
    return proc


def send_test_email(values, timeout=30):
    """Send a test email using the given (form) values.

    Mirrors the original server's send_email (smtplib + STARTTLS), except
    that port 465 uses implicit SSL (STARTTLS is not offered there).
    ``timeout`` bounds every socket operation (connect, read, send) so a
    dead SMTP server fails fast instead of blocking for minutes.
    Raises on any error; returns the recipient on success.
    """
    import smtplib
    from email.mime.text import MIMEText

    email_from = values.get("EMAIL_FROM", "").strip()
    email_to = values.get("EMAIL_TO", "").strip()
    smtp_server = values.get("SMTP_SERVER", "").strip()
    smtp_port = values.get("SMTP_PORT", "").strip() or "587"
    smtp_user = values.get("SMTP_USER", "").strip()
    smtp_password = values.get("SMTP_PASSWORD", "")

    missing = [name for name, val in (
        ("E-Mail Absender", email_from), ("E-Mail Empfaenger", email_to),
        ("SMTP Server", smtp_server), ("SMTP Benutzer", smtp_user),
        ("SMTP Passwort", smtp_password.strip())) if not val]
    if missing:
        raise ValueError("Bitte zuerst ausfuellen: " + ", ".join(missing))

    msg = MIMEText("Dies ist eine Test-E-Mail des wsciot GUI Launchers.\n"
                   "Wenn Sie diese Mail erhalten, funktioniert der E-Mail-Versand.\n")
    msg["Subject"] = "[wsciot] Test-E-Mail"
    msg["From"] = email_from
    msg["To"] = email_to

    port = int(smtp_port)
    if port == 465:
        server = smtplib.SMTP_SSL(smtp_server, port, timeout=timeout)
    else:
        server = smtplib.SMTP(smtp_server, port, timeout=timeout)
    try:
        if port != 465:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except OSError:
            pass
    return email_to


def stop_server(pid):
    """Terminate the server process tree (server first, then children)."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True)
    else:
        import signal
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def alive(pid):
    """True if a process with this PID exists AND is not a zombie/ours."""
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, timeout=10,
            ).stdout
            if isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            if not out:
                return False
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
