# SPDX-FileCopyrightText: 2026 Stefan Helmert
#
# SPDX-License-Identifier: AGPL-3.0

"""wsciot GUI launcher - a friendly window around the original wsciot server.

The original wsciot server (``../wsciot``) is NOT modified. This GUI:

* reads the ``.env`` configuration file and shows the values in text fields
* writes changes back to ``.env`` on "Save"
* starts the original server in the background ("Start Server")
* stops it again ("Stop Server")
* shows whether the server is running and displays its console log

The GUI can be closed while the server keeps running; on the next start
the GUI re-attaches to the still-running server via its PID file.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

from wsciot_gui import logic

APP_TITLE = "Wassersammler IoT - Server Verwaltung"
REFRESH_MS = 2000        # status/health polling interval
LOG_POLL_MS = 400        # console log tail interval
STOP_POLL_MS = 150       # server-stop completion polling interval


class GuiLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x680")
        self.minsize(760, 560)

        self.server_dir = logic.find_server_dir()
        self.env_path = logic.default_env_path()
        self.proc = None                    # Popen handle if we started it
        self._log_pos = 0                   # read position in the server log
        self._stopping = False              # True while taskkill runs
        self.status_var = tk.StringVar(value="unbekannt")
        self.log_path = Path.home() / ".wsciot_gui_server.log"

        self._build_ui()
        self._load_env()
        self._refresh_status()
        self.after(REFRESH_MS, self._poll_status)
        self.after(LOG_POLL_MS, self._poll_log)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, **pad)

        # status row
        status_frame = ttk.LabelFrame(top, text="Server Status")
        status_frame.pack(fill="x", **pad)
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                      font=("", 11, "bold"))
        self.status_label.grid(row=0, column=1, sticky="w", padx=6)
        self.pid_label = ttk.Label(status_frame, text="")
        self.pid_label.grid(row=0, column=2, sticky="w", padx=12)

        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btn_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(btn_frame, text="Stop Server", command=self.stop_server)
        self.stop_btn.pack(side="left", padx=4)
        self.save_btn = ttk.Button(btn_frame, text="Save", command=self.save_env)
        self.save_btn.pack(side="left", padx=4)
        self.reload_btn = ttk.Button(btn_frame, text="Neu laden", command=self._load_env)
        self.reload_btn.pack(side="left", padx=4)
        self.open_log_btn = ttk.Button(btn_frame, text="Log-Datei öffnen", command=self._open_log_file)
        self.open_log_btn.pack(side="left", padx=4)
        self.test_mail_btn = ttk.Button(btn_frame, text="Test-E-Mail senden",
                                        command=self.send_test_email)
        self.test_mail_btn.pack(side="left", padx=4)
        self.help_btn = ttk.Button(btn_frame, text="Hilfe", command=self.show_help)
        self.help_btn.pack(side="right", padx=4)

        # config section
        cfg = ttk.LabelFrame(top, text="Konfiguration (.env)")
        cfg.pack(fill="x", **pad)
        # column 1 (the entry fields) stretches when the window is widened
        cfg.columnconfigure(1, weight=1)
        self.entries = {}
        for i, (key, label, secret) in enumerate(logic.ENV_FIELDS):
            lbl = ttk.Label(cfg, text=label + ":")
            lbl.grid(row=i, column=0, sticky="e", padx=6, pady=2)
            ent = ttk.Entry(cfg, show="*" if secret else "")
            ent.grid(row=i, column=1, sticky="ew", padx=6, pady=2)
            show_btn = ttk.Button(cfg, text="zeigen", width=6,
                                  command=lambda e=ent: self._toggle_show(e))
            show_btn.grid(row=i, column=2, padx=2)
            self.entries[key] = ent
            self._add_context_menu(ent, editable=True)
        if self.server_dir is None:
            warn = ttk.Label(cfg, text="Achtung: wsciot-Serverpaket wurde nicht gefunden!",
                             foreground="red")
            warn.grid(row=len(logic.ENV_FIELDS), column=0, columnspan=3, sticky="w", padx=6)

        # log section
        log_frame = ttk.LabelFrame(top, text="Server-Konsole (Log)")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=12, width=110,
                                                 state="disabled", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)
        self._add_context_menu(self.log_box, editable=False)

    # --------------------------------------------------- context menu
    def _add_context_menu(self, widget, editable=True):
        """Attach the usual right-click menu (cut/copy/paste/select all)."""
        menu = tk.Menu(widget, tearoff=0)

        def do_cut():
            widget.event_generate("<<Cut>>")
            # <<Cut>> only clears the selection, not the entry, on some
            # platforms without default bindings - enforce for Entry
            if editable and isinstance(widget, tk.Entry):
                try:
                    widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass

        def do_copy():
            widget.event_generate("<<Copy>>")

        def do_paste():
            widget.event_generate("<<Paste>>")

        def do_select_all():
            if isinstance(widget, tk.Entry):
                widget.select_range(0, "end")
                widget.icursor("end")
            else:
                widget.tag_add("sel", "1.0", "end")

        def popup(event):
            menu.delete(0, "end")
            if editable:
                menu.add_command(label="Ausschneiden", command=do_cut)
            menu.add_command(label="Kopieren", command=do_copy)
            if editable:
                menu.add_command(label="Einfügen", command=do_paste)
            menu.add_separator()
            menu.add_command(label="Alles markieren", command=do_select_all)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"

        widget.bind("<Button-3>", popup)
        widget.bind("<Button-2>", popup)   # some systems/scroll wheels

    # --------------------------------------------------------------- .env
    def _load_env(self):
        env = logic.read_env(self.env_path)
        for key, _label, _secret in logic.ENV_FIELDS:
            self.entries[key].delete(0, "end")
            value = env.get(key, "")
            if not value:
                # port fields: show the server's built-in default, which
                # applies when the .env line is omitted (see logic.write_env)
                value = logic.PORT_DEFAULTS.get(key, "")
            self.entries[key].insert(0, value)
        if env:
            self._log_append(f"[GUI] Konfiguration geladen: {self.env_path}\n")
        else:
            self._log_append(f"[GUI] Noch keine Konfiguration vorhanden ({self.env_path}).\n")

    def save_env(self, show_info=True):
        values = {k: e.get().strip() for k, e in self.entries.items()}
        missing = [k for k in ("TTN_APP_ID", "TTN_ACCESS_KEY", "EMAIL_FROM",
                               "EMAIL_TO", "SMTP_SERVER", "SMTP_USER", "SMTP_PASSWORD")
                   if not values.get(k)]
        if missing:
            if not messagebox.askyesno(
                    "Unvollständige Angaben",
                    "Diese Felder sind leer:\n  - " + "\n  - ".join(missing) +
                    "\n\nTrotzdem speichern?"):
                return
        logic.write_env(self.env_path, values)
        self._log_append(f"[GUI] Konfiguration gespeichert: {self.env_path}\n")
        if show_info:
            messagebox.showinfo("Gespeichert",
                            "Konfiguration gespeichert.\n\nHinweis: Der Server liest die "
                            "Konfiguration nur beim Start. Starten Sie den Server neu, "
                            "damit Änderungen wirksam werden.")

    # ----------------------------------------------------------------- help
    def show_help(self):
        """Non-blocking help dialog: quick guide + FAQ (all in main thread)."""
        win = tk.Toplevel(self)
        win.title("Hilfe - Server Verwaltung")
        win.geometry("660x580")
        win.transient(self)
        txt = scrolledtext.ScrolledText(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self._fill_help_text(txt)
        txt.config(state="disabled")
        self._add_context_menu(txt, editable=False)
        ttk.Button(win, text="Schließen", command=win.destroy).pack(pady=(0, 8))
        win.grab_set()

    def _fill_help_text(self, txt):
        txt.tag_configure("h", font=("", 12, "bold"), spacing3=2)
        txt.tag_configure("q", font=("", 10, "bold"), spacing1=8)

        def h(text):
            txt.insert("end", text + "\n", "h")

        def q(text):
            txt.insert("end", text + "\n", "q")

        def p(text=""):
            txt.insert("end", text + "\n")

        h("Kurzanleitung")
        p("1. Zugangsdaten (TTN, E-Mail/SMTP) in die Felder eintragen.")
        p('2. "Save" klicken - damit werden die Daten in die Konfigurationsdatei '
          "geschrieben. Sie liegt im Ordner der Server-Software und wird von "
          "dieser GUI verwaltet.")
        p('3. "Start Server" klicken. Nach ein paar Sekunden zeigt der Status LÄUFT.')
        p("4. Ab jetzt verschickt der Server automatisch eine E-Mail, sobald ein "
          "Wassersammler meldet, dass er voll ist.")
        p("5. Diese GUI kann geschlossen werden - der Server läuft im Hintergrund "
          "weiter und wird beim nächsten Start der GUI wieder erkannt.")
        p()
        h("Häufige Fragen")
        q("Muss ich speichern, bevor ich den Server starte?")
        p("Ja. Der Server liest die Konfiguration nur beim Start. Änderungen, die "
          "nur in den Textfeldern stehen, ignoriert er. Deshalb fragt die GUI vor "
          "dem Start von selbst nach, wenn es ungespeicherte Änderungen gibt - mit "
          'einfachem "Ja" wird automatisch gespeichert.')
        q("Ich habe Daten geändert - Server neu starten oder nur neu laden?")
        p("Der Server muss neu gestartet werden, um Änderungen zu übernehmen:")
        p('  1. "Save" klicken')
        p('  2. "Stop Server" klicken')
        p('  3. "Start Server" klicken')
        p('"Neu laden" betrifft nur die Textfelder: Es lädt die gespeicherte '
          "Konfiguration in die Felder zurück (und verwirft damit ungespeicherte "
          "Eingaben). Am laufenden Server ändert es nichts.")
        q("Was macht \"Test-E-Mail senden\"?")
        p("Es prüft die E-Mail-Einstellungen, ohne den Server zu starten. Dabei "
          "werden die aktuellen Feldwerte benutzt - vorher speichern ist nicht "
          "nötig. Kommt die Test-E-Mail an, kann auch der Server Mails verschicken.")
        q("Was bedeutet der Status?")
        p("LÄUFT: Der Serverprozess läuft. Er baut nach dem Start zuerst die "
          "Verbindung zum TTN-Netz auf; das dauert ein paar Sekunden.")
        p("GESTOPPT: Es läuft kein Server - es werden keine E-Mails verschickt.")
        q("Wo finde ich die Dateien?")
        p("Die Konfiguration (.env) liegt im Ordner der Server-Software "
          "(src/software/wsciot). Sie wird direkt von dieser GUI verwaltet - "
          'Sie müssen sie nie von Hand öffnen; "Save" schreibt sie.')
        p("Das Server-Log liegt in Ihrem Benutzerordner "
          f"({self.log_path.name}) und kann bequem über den Button "
          '"Log-Datei öffnen" angezeigt werden.')
        q("Im Log steht ein Fehler - was tun?")
        p("Meist hilft: Konfiguration prüfen, \"Save\", Server stoppen und wieder "
          'starten. Bei E-Mail-Problemen zuerst "Test-E-Mail senden" verwenden - '
          "es nennt die genaue Fehlerursache (z. B. falsches Passwort).")

    def _effective_values(self):
        """Current form values as they would be written to the .env."""
        values = {k: e.get().strip() for k, e in self.entries.items()}
        ttn_app_id = values.get("TTN_APP_ID", "")
        effective = {}
        for key, val in values.items():
            if key in logic.PORT_DEFAULTS and (not val or val == logic.PORT_DEFAULTS[key]):
                continue
            if key == "MQTT_TOPIC" and val:
                val = val.replace("{TTN_APP_ID}", ttn_app_id)
            effective[key] = val
        return effective

    def _unsaved_changes(self):
        """True if the text fields differ from the stored .env."""
        env = logic.read_env(self.env_path)
        return any(env.get(k, "") != v for k, v in self._effective_values().items())

    # ------------------------------------------------------- test email
    MAIL_TEST_TIMEOUT_S = 12   # hard socket timeout for the SMTP worker
    MAIL_POLL_MS = 100         # queue polling interval

    def send_test_email(self):
        """Send a test mail without freezing the GUI.

        Pattern (thread-safe with tkinter): a worker thread only runs the
        blocking SMTP call and puts its result into a queue - it NEVER
        touches any widget or Tk method. All GUI access (button state,
        log, dialogs) happens here in the main thread, driven by an
        after() timer that polls the queue.
        """
        # read form values in the MAIN thread, pass as plain data
        values = {k: e.get() for k, e in self.entries.items()}
        self.test_mail_btn.config(state="disabled")
        self._log_append("[GUI] Sende Test-E-Mail...\n")
        self.mail_q = queue.Queue()
        threading.Thread(
            target=self._test_mail_worker, args=(values,), daemon=True).start()
        self.after(self.MAIL_POLL_MS, self._poll_mail_queue)

    def _test_mail_worker(self, values):
        """Worker thread: blocking I/O only, NO GUI access in here."""
        try:
            recipient = logic.send_test_email(values, timeout=self.MAIL_TEST_TIMEOUT_S)
            self.mail_q.put(("ok", recipient))
        except Exception as e:  # ValueError, SMTP errors, DNS, timeouts...
            self.mail_q.put(("error", f"{type(e).__name__}: {e}"))

    def _poll_mail_queue(self):
        """Timer callback (main thread): drain the queue, update the GUI."""
        try:
            kind, detail = self.mail_q.get_nowait()
        except queue.Empty:
            self.after(self.MAIL_POLL_MS, self._poll_mail_queue)
            return
        self.test_mail_btn.config(state="normal")
        self._test_mail_result(kind == "ok", detail)

    def _test_mail_result(self, ok, detail):
        if ok:
            self._log_append(f"[GUI] Test-E-Mail erfolgreich versendet an {detail}.\n")
            messagebox.showinfo("Test-E-Mail",
                                f"Test-E-Mail erfolgreich versendet an:\n{detail}\n\n"
                                "Bitte Postfach pruefen (auch Spam-Ordner).")
        else:
            self._log_append(f"[GUI] Test-E-Mail FEHLGESCHLAGEN: {detail}\n")
            messagebox.showerror("Test-E-Mail fehlgeschlagen",
                                 f"Der Versand ist fehlgeschlagen:\n\n{detail}\n\n"
                                 "Bitte SMTP-Einstellungen und Passwort pruefen.")

    # ------------------------------------------------------------- server
    def start_server(self):
        if self._server_alive():
            messagebox.showinfo("Läuft bereits", "Der Server läuft bereits.")
            return
        if self.server_dir is None:
            messagebox.showerror("Fehler", "wsciot-Serverpaket nicht gefunden.")
            return
        if self._unsaved_changes():
            if messagebox.askyesno(
                    "Ungespeicherte Änderungen",
                    "Es gibt ungespeicherte Änderungen in den Textfeldern.\n\n"
                    "Der Server liest die Konfiguration nur beim Start. Sollen "
                    "die Änderungen jetzt gespeichert werden, damit er sie "
                    "übernimmt?"):
                self.save_env(show_info=False)
        cmd, python_exe = logic.find_python_and_launch_cmd(self.server_dir)
        self._log_append(f"[GUI] Starte Server: {' '.join(cmd)} (Arbeitsverzeichnis: {self.server_dir})\n")
        try:
            self.proc = logic.start_server(self.server_dir, python_exe, self.log_path)
        except OSError as e:
            messagebox.showerror("Fehler beim Start", str(e))
            return
        Path(self.server_dir, ".wsciot_gui.pid").write_text(str(self.proc.pid), encoding="utf-8")
        self._log_pos = 0   # show the new server's output from the beginning
        self._refresh_status()
        # note: the server needs a few seconds until the MQTT connection is up

    def stop_server(self):
        """Stop the server without blocking the GUI.

        taskkill runs detached (logic.stop_server); this handler only
        starts it and polls the completion queue via after() - all GUI
        access stays in the main thread.
        """
        pid = self._running_pid()
        if not pid:
            messagebox.showinfo("Nicht gestartet", "Der Server läuft nicht.")
            return
        if not messagebox.askyesno("Server beenden",
                                   "Server wirklich beenden? Es werden dann keine "
                                   "Benachrichtigungen mehr per E-Mail verschickt!"):
            return
        self.stop_q = queue.Queue()
        logic.stop_server(pid, on_done=lambda killed: self.stop_q.put(killed))
        self._log_append(f"[GUI] Beende Server (PID {pid})...\n")
        self._stopping = True
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.after(STOP_POLL_MS, self._poll_stop_queue)

    def _poll_stop_queue(self):
        """Timer callback (main thread): show the stop result."""
        try:
            killed = self.stop_q.get_nowait()
        except queue.Empty:
            self.after(STOP_POLL_MS, self._poll_stop_queue)
            return
        self._stopping = False
        if killed:
            self.proc = None
            if self.server_dir:
                try:
                    Path(self.server_dir, ".wsciot_gui.pid").unlink()
                except OSError:
                    pass
            self._log_append("[GUI] Server gestoppt.\n")
        else:
            self._log_append("[GUI] Server konnte nicht beendet werden "
                             "(Prozess evtl. bereits beendet).\n")
        self._refresh_status()

    def _running_pid(self):
        """Return the PID of the running server, if any."""
        if self.proc is not None and self.proc.poll() is None:
            return self.proc.pid
        if self.server_dir:
            pid_file = Path(self.server_dir) / ".wsciot_gui.pid"
        else:
            pid_file = None
        if pid_file and pid_file.is_file():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return None
            if logic.alive(pid):
                return pid
        return None

    def _server_alive(self):
        return self._running_pid() is not None

    # -------------------------------------------------------------- status
    def _refresh_status(self):
        pid = self._running_pid()
        if pid:
            self.status_var.set("LÄUFT")
            self.status_label.config(foreground="green")
            self.pid_label.config(text=f"(PID {pid})")
        else:
            self.status_var.set("GESTOPPT")
            self.status_label.config(foreground="red")
            self.pid_label.config(text="")
        self.start_btn.config(state="disabled" if pid else "normal")
        self.stop_btn.config(state="normal" if pid else "disabled")

    def _poll_status(self):
        self._refresh_status()
        self.after(REFRESH_MS, self._poll_status)

    # ----------------------------------------------------------------- log
    def _poll_log(self):
        """Timer callback: append new log file content (non-blocking read)."""
        try:
            if self.log_path.is_file():
                size = self.log_path.stat().st_size
                if size < self._log_pos:      # log rotated/truncated
                    self._log_pos = 0
                if size > self._log_pos:
                    with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(self._log_pos)
                        chunk = f.read()
                        self._log_pos = f.tell()
                    self._log_append(chunk)
        except OSError:
            pass
        self.after(LOG_POLL_MS, self._poll_log)

    def _log_append(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert("end", text)
        # cap the log box at ~2000 lines
        if int(self.log_box.index("end-1c").split(".")[0]) > 2000:
            self.log_box.delete("1.0", "200.0")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _toggle_show(self, entry):
        entry.config(show="" if entry.cget("show") else "*")

    def _open_log_file(self):
        try:
            import subprocess as sp
            sp.Popen(["notepad.exe", str(self.log_path)])
        except OSError:
            pass

    # -------------------------------------------------------------- close
    def _on_close(self):
        # The server keeps running when the GUI is closed.
        self.destroy()


def main():
    app = GuiLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
