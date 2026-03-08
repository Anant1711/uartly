import serial
import serial.tools.list_ports
import time
import argparse
import threading
import sys
from datetime import datetime
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog

class ModernSerialLoggerGUI:
    def __init__(self):
        self.ser = None
        self.running = False
        self.full_log_history = []
        self.terminal_window = None
        self.terminal_box = None
        self.terminal_line_ending = None
        
        # UI State
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.log_font = ("Consolas", 13) if sys.platform.startswith("win") else ("Monospace", 12)
        self.baudrate_options = ["9600", "115200", "230400", "460800", "921600"]
        
        self.setup_gui()
        self.refresh_ports()

    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Advanced Serial Terminal")
        self.root.geometry("1400x950")

        # --- 1. TOP NAVIGATION BAR ---
        nav_bar = ctk.CTkFrame(self.root, height=40, corner_radius=0, fg_color=("#DBDBDB", "#2B2B2B"))
        nav_bar.pack(side="top", fill="x")
        
        ctk.CTkLabel(nav_bar, text="⚙️ SYSTEM OPTIONS", font=("Arial", 12, "bold")).pack(side="left", padx=20)
        ctk.CTkButton(nav_bar, text="🖥  Open Terminal", width=140, command=self.open_terminal_window,
                      fg_color="#1E3A5F", hover_color="#2E5A8F").pack(side="left", padx=12, pady=5)

        self.theme_switch = ctk.CTkOptionMenu(nav_bar, values=["Dark", "Light"], 
                                             command=self.change_theme, width=100)
        self.theme_switch.set("Dark")
        self.theme_switch.pack(side="right", padx=10, pady=5)
        ctk.CTkLabel(nav_bar, text="Theme:", font=("Arial", 12)).pack(side="right", padx=5)

        # --- 2. CONTROL PANEL ---
        control_frame = ctk.CTkFrame(self.root)
        control_frame.pack(fill="x", padx=20, pady=10)

        # Port & Baud
        port_group = ctk.CTkFrame(control_frame, fg_color="transparent")
        port_group.pack(side="left", padx=10)
        self.port_menu = ctk.CTkOptionMenu(port_group, width=140)
        self.port_menu.pack(side="left", padx=5)
        ctk.CTkButton(port_group, text="🔄", width=30, command=self.refresh_ports).pack(side="left")
        
        self.baud_menu = ctk.CTkOptionMenu(port_group, values=self.baudrate_options, width=100)
        self.baud_menu.set("115200")
        self.baud_menu.pack(side="left", padx=10)

        # Filter Group
        filter_group = ctk.CTkFrame(control_frame, fg_color="transparent")
        filter_group.pack(side="left", padx=20)
        self.filter_entry = ctk.CTkEntry(filter_group, width=180, placeholder_text="Filter logs...")
        self.filter_entry.pack(side="left", padx=5)
        self.filter_entry.bind("<Return>", lambda e: self.apply_filter())
        
        self.exact_match_var = tk.BooleanVar(value=False)
        self.exact_check = ctk.CTkCheckBox(filter_group, text="Exact Match", variable=self.exact_match_var, 
                                          font=("Arial", 11), checkbox_width=18, checkbox_height=18)
        self.exact_check.pack(side="left", padx=5)

        # Connect/Save/Clear
        btns_group = ctk.CTkFrame(control_frame, fg_color="transparent")
        btns_group.pack(side="right", padx=10)
        self.start_btn = ctk.CTkButton(btns_group, text="Connect", width=100, command=self.toggle_logging, fg_color="#28B463")
        self.start_btn.pack(side="left", padx=5)
        ctk.CTkButton(btns_group, text="Save All", width=80, command=self.save_all_logs).pack(side="left", padx=5)
        ctk.CTkButton(btns_group, text="Clear", width=70, command=self.clear_logs, fg_color="#922B21").pack(side="left", padx=5)

        # --- 3. RESIZABLE PANELS ---
        self.paned_window = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#1a1a1a", sashwidth=6, bd=0)
        self.paned_window.pack(fill="both", expand=True, padx=20, pady=10)

        self.all_logs_box = self.create_log_viewer(self.paned_window, "MAIN LOG FEED", "#5dade2")
        self.filtered_logs_box = self.create_log_viewer(self.paned_window, "FILTERED RESULTS", "#f4d03f")

        self.paned_window.add(self.all_logs_box.master, height=400)
        self.paned_window.add(self.filtered_logs_box.master, height=300)

        # --- 4. SEND / TERMINAL BAR ---
        send_frame = ctk.CTkFrame(self.root, height=50)
        send_frame.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(send_frame, text="TX:", font=("Arial", 12, "bold"), text_color="#58D68D").pack(side="left", padx=(10, 4))

        self.send_entry = ctk.CTkEntry(send_frame, font=self.log_font, placeholder_text="Type command and press Enter or Send...")
        self.send_entry.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        self.send_entry.bind("<Return>", lambda e: self.send_data())

        self.line_ending_menu = ctk.CTkOptionMenu(send_frame, values=["CR+LF", "LF", "CR", "None"], width=90)
        self.line_ending_menu.set("CR+LF")
        self.line_ending_menu.pack(side="left", padx=5)

        ctk.CTkButton(send_frame, text="Send", width=80, command=self.send_data, fg_color="#1A5276").pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(self.root, text="System Ready", font=("Arial", 12))
        self.status_label.pack(side="left", padx=20, pady=5)

    def create_log_viewer(self, parent, title, accent_color):
        container = ctk.CTkFrame(parent, corner_radius=0)
        ctk.CTkLabel(container, text=f"  {title}", font=("Arial", 11, "bold"), text_color=accent_color).pack(anchor="w", pady=2)
        
        # wrap="none" is key here to allow the horizontal line to stay on one row
        box = ctk.CTkTextbox(container, font=self.log_font, border_width=1, state="disabled", wrap="none")
        box.pack(fill="both", expand=True, padx=5, pady=5)
        return box

    def add_row(self, widget, message):
        """Requirement: Row line spans full width and remains read-only"""
        widget.configure(state="normal")
        # Using a very long line of characters ensures it hits the edge of any 4K monitor.
        # Combined with wrap="none", this creates a consistent horizontal divider.
        full_width_line = "─" * 500 
        widget.insert("end", f" {message}\n{full_width_line}\n")
        widget.configure(state="disabled")
        widget.see("end")

    def apply_filter(self):
        search_term = self.filter_entry.get()
        exact = self.exact_match_var.get()
        
        self.filtered_logs_box.configure(state="normal")
        self.filtered_logs_box.delete("1.0", "end")
        self.filtered_logs_box.configure(state="disabled")
        
        matches = []
        for entry in self.full_log_history:
            raw_message = entry.split(" » ")[-1]
            if exact:
                if search_term == raw_message: matches.append(entry)
            else:
                if search_term.lower() in raw_message.lower(): matches.append(entry)
        
        for m in matches: self.add_row(self.filtered_logs_box, m)
        self.status_label.configure(text=f"Filter: {len(matches)} matches found.")

    def change_theme(self, choice):
        ctk.set_appearance_mode(choice.lower())
        bg_color = "#1a1a1a" if choice == "Dark" else "#d1d1d1"
        self.paned_window.configure(bg=bg_color)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports: ports = ["No Ports Found"]
        self.port_menu.configure(values=ports)
        self.port_menu.set(ports[0])

    def read_serial(self):
        import re
        # Pattern to match logs like: 2026-02-24T20:05:58:
        log_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
        
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    if not raw_data: continue
                    
                    text = raw_data.decode("utf-8", errors="ignore")
                    stripped = text.strip()
                    
                    if stripped:
                        is_log = bool(log_pattern.search(stripped))
                        term_text = text.replace("\r", "")

                        if self.terminal_box:
                            # Terminal is OPEN:
                            #   - App logs (timestamp match) → main log feed only
                            #   - Shell/device output        → terminal only
                            if is_log:
                                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                log_entry = f"[{ts}] » {stripped}"
                                self.full_log_history.append(log_entry)
                                self.root.after(0, self.add_row, self.all_logs_box, log_entry)

                                exact = self.exact_match_var.get()
                                search_term = self.filter_entry.get()
                                if (exact and search_term == stripped) or \
                                   (not exact and search_term and search_term.lower() in stripped.lower()):
                                    self.root.after(0, self.add_row, self.filtered_logs_box, log_entry)
                            else:
                                # Shell / device echo → terminal window only
                                self.root.after(0, self.terminal_append_raw, term_text, "rx")
                        else:
                            # Terminal is CLOSED:
                            #   - ALL lines → main log feed (boot messages, kernel output, etc.)
                            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            log_entry = f"[{ts}] » {stripped}"
                            self.full_log_history.append(log_entry)
                            self.root.after(0, self.add_row, self.all_logs_box, log_entry)

                            exact = self.exact_match_var.get()
                            search_term = self.filter_entry.get()
                            if (exact and search_term == stripped) or \
                               (not exact and search_term and search_term.lower() in stripped.lower()):
                                self.root.after(0, self.add_row, self.filtered_logs_box, log_entry)
                else:
                    time.sleep(0.01)
            except: break

    def toggle_logging(self):
        if self.running: self.stop_logging()
        else: self.start_logging()

    def start_logging(self):
        try:
            self.ser = serial.Serial(port=self.port_menu.get(), baudrate=int(self.baud_menu.get()), timeout=0.1)
            self.running = True
            self.start_btn.configure(text="Disconnect", fg_color="#C0392B")
            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")

    def stop_logging(self):
        self.running = False
        if self.ser: self.ser.close()
        self.start_btn.configure(text="Connect", fg_color="#28B463")

    def send_data(self):
        if not self.running or not self.ser:
            self.status_label.configure(text="Not connected – cannot send.")
            return
        text = self.send_entry.get()
        if not text:
            return
        ending = self.line_ending_menu.get()
        suffix = {"CR+LF": b"\r\n", "LF": b"\n", "CR": b"\r", "None": b""}.get(ending, b"\r\n")
        try:
            self.ser.write(text.encode("utf-8") + suffix)
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = f"[{ts}] TX » {text}"
            self.full_log_history.append(log_entry)
            self.root.after(0, self.add_row, self.all_logs_box, log_entry)
            self.send_entry.delete(0, "end")
        except Exception as e:
            self.status_label.configure(text=f"Send error: {e}")

    # ── DETACHED TERMINAL WINDOW ──────────────────────────────────────────────
    def open_terminal_window(self):
        """Open (or focus) a separate interactive terminal window."""
        if self.terminal_window and self.terminal_window.winfo_exists():
            self.terminal_window.focus_force()
            return

        self._term_input_buffer = ""      # current line being typed
        self._term_cmd_history  = []      # sent commands history
        self._term_hist_idx     = -1      # history navigation index
        self._term_line_ending  = "CR+LF" # default line ending

        win = ctk.CTkToplevel(self.root)
        win.title("Serial Terminal")
        win.geometry("900x620")
        win.protocol("WM_DELETE_WINDOW", self._close_terminal_window)
        self.terminal_window = win

        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = ctk.CTkFrame(win, height=36, corner_radius=0, fg_color=("#111", "#111"))
        title_bar.pack(fill="x")

        ctk.CTkLabel(title_bar, text="🖥  SERIAL TERMINAL  —  type directly in the screen",
                     font=("Arial", 11, "bold"), text_color="#58D68D").pack(side="left", padx=12)

        # Line-ending selector in title bar
        ctk.CTkLabel(title_bar, text="LF:", font=("Arial", 10),
                     text_color="#aaa").pack(side="right", padx=(0, 2))
        self._term_le_menu = ctk.CTkOptionMenu(
            title_bar, values=["CR+LF", "LF", "CR", "None"], width=90,
            command=self._set_term_line_ending)
        self._term_le_menu.set("CR+LF")
        self._term_le_menu.pack(side="right", padx=(0, 8), pady=4)

        ctk.CTkButton(title_bar, text="Clear", width=55,
                      command=self._clear_terminal,
                      fg_color="#7B241C", hover_color="#922B21").pack(side="right", padx=4, pady=4)

        # ── Main terminal Text widget (the ONLY area, no bottom input bar) ──
        frame = tk.Frame(win, bg="#0d0d0d")
        frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame, bg="#222", troughcolor="#111", activebackground="#555")
        scrollbar.pack(side="right", fill="y")

        self.terminal_box = tk.Text(
            frame,
            bg="#0d0d0d", fg="#39FF14",
            insertbackground="#39FF14",
            insertwidth=2,
            font=self.log_font,
            wrap="char",
            relief="flat", bd=0,
            yscrollcommand=scrollbar.set,
            state="normal",
            cursor="xterm",
        )
        self.terminal_box.tag_configure("tx",  foreground="#5dade2")   # sent (blue)
        self.terminal_box.tag_configure("rx",  foreground="#39FF14")   # received (green)
        self.terminal_box.tag_configure("sys", foreground="#888888")   # system info (grey)
        scrollbar.configure(command=self.terminal_box.yview)
        self.terminal_box.pack(fill="both", expand=True)

        # Mark the "protected" boundary — nothing before this can be edited
        self.terminal_box.insert("end",
            "─── Serial Terminal  (raw interactive mode) ───\n",
            "sys")

        # ── Bind keys ────────────────────────────────────────────────────────
        tb = self.terminal_box

        # Block most default key handling, re-route through our handlers
        tb.bind("<Key>",           self._term_key,        add=False)
        tb.bind("<Return>",        self._term_enter,      add=False)
        tb.bind("<BackSpace>",     self._term_backspace,  add=False)
        tb.bind("<Delete>",        self._term_delete,     add=False)
        tb.bind("<Up>",            self._term_up,         add=False)
        tb.bind("<Down>",          self._term_down,       add=False)
        tb.bind("<Left>",          self._term_left,       add=False)
        tb.bind("<Right>",         self._term_right,      add=False)
        # Ctrl combos
        tb.bind("<Control-c>",      self._term_ctrl_c,     add=False)
        tb.bind("<Control-C>",      self._term_ctrl_c,     add=False)
        tb.bind("<Control-v>",      self._term_ctrl_v,     add=False)
        tb.bind("<Control-V>",      self._term_ctrl_v,     add=False)
        tb.bind("<Control-d>",     self._term_ctrl_d,     add=False)
        tb.bind("<Control-l>",     self._term_ctrl_l,     add=False)
        tb.bind("<Control-L>",     self._term_ctrl_l,     add=False)

        # Allow normal mouse click/drag for text selection
        # (no break — let tkinter handle selection natively)

        tb.focus_set()

    # ── Internal terminal helpers ─────────────────────────────────────────────

    def _set_term_line_ending(self, choice):
        self._term_line_ending = choice

    def _send_raw_bytes(self, data):
        if self.running and self.ser:
            try:
                self.ser.write(data)
            except Exception:
                pass

    def _term_key(self, event):
        """Send printable characters immediately to the device."""
        if event.char and event.char.isprintable() and not (event.state & 0x4):  # not Ctrl
            self._send_raw_bytes(event.char.encode("utf-8"))
        return "break"  # prevent default tk insertion

    def _term_enter(self, event=None):
        """Send line ending."""
        suffix = {"CR+LF": b"\r\n", "LF": b"\n", "CR": b"\r", "None": b""}.get(
            self._term_line_ending, b"\r\n")
        self._send_raw_bytes(suffix)
        return "break"

    def _term_backspace(self, event=None):
        # Just send raw BS byte — device handles echo/deletion like a real terminal
        self._send_raw_bytes(b"\x08")
        return "break"

    def _term_delete(self, event=None):
        self._send_raw_bytes(b"\x7f")  # DEL
        return "break"

    def _term_up(self, event=None):
        self._send_raw_bytes(b"\x1b[A")
        return "break"

    def _term_down(self, event=None):
        self._send_raw_bytes(b"\x1b[B")
        return "break"

    def _term_left(self, event=None):
        self._send_raw_bytes(b"\x1b[D")
        return "break"

    def _term_right(self, event=None):
        self._send_raw_bytes(b"\x1b[C")
        return "break"

    def _term_ctrl_c(self, event=None):
        """Ctrl+C: copy selected text if any, otherwise send SIGINT (0x03)."""
        tb = self.terminal_box
        try:
            selected = tb.get("sel.first", "sel.last")
            if selected:
                # Copy selection to clipboard
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                return "break"
        except Exception:
            pass
        # No selection — send SIGINT
        self._send_raw_bytes(b"\x03")
        return "break"

    def _term_ctrl_v(self, event=None):
        """Ctrl+V: paste clipboard text and send to serial device."""
        try:
            text = self.root.clipboard_get()
            if text:
                self._send_raw_bytes(text.encode("utf-8"))
        except Exception:
            pass
        return "break"

    def _term_ctrl_d(self, event=None):
        self._send_raw_bytes(b"\x04")
        return "break"

    def _term_ctrl_l(self, event=None):
        self._clear_terminal()
        return "break"

    def terminal_append_raw(self, text, tag="rx"):
        """Append raw RX data into the terminal, stripping ANSI escape codes."""
        import re
        if not self.terminal_box:
            return
        try:
            tb = self.terminal_box
            # NOTE: keep state=normal always so the cursor remains visible

            # Strip all ANSI/VT100 escape sequences (colors, cursor commands, etc.)
            ansi_escape = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[()][AB012]|\x1b[=>]|\x1b[MDE78HFc]")
            text = ansi_escape.sub("", text)

            # Handle \r (carriage return): only keep last segment per line
            lines = text.split("\n")
            cleaned_lines = []
            for line in lines:
                if "\r" in line:
                    line = line.split("\r")[-1]
                cleaned_lines.append(line)
            text = "\n".join(cleaned_lines)

            # Handle backspace (\x08) for visual cleanup
            while "\x08" in text:
                idx = text.find("\x08")
                if idx > 0:
                    text = text[:idx-1] + text[idx+1:]
                else:
                    if tb.index("end-1c") != "1.0":
                        tb.delete("end-2c", "end-1c")
                    text = text[1:]

            if text:
                tb.insert("end", text, tag)
                tb.see("end")
        except Exception:
            pass

    def _clear_terminal(self):
        if not self.terminal_box:
            return
        tb = self.terminal_box
        tb.delete("1.0", "end")
        tb.insert("end", "─── Screen cleared ───\n", "sys")

    def _close_terminal_window(self):
        self.terminal_box = None
        self.terminal_window.destroy()
        self.terminal_window = None

    def clear_logs(self):
        for box in [self.all_logs_box, self.filtered_logs_box]:
            box.configure(state="normal")
            box.delete("1.0", "end")
            box.configure(state="disabled")
        self.full_log_history.clear()

    def save_all_logs(self):
        if not self.full_log_history: return
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.full_log_history))

    def run(self):
        self.root.mainloop()

def main():
    app = ModernSerialLoggerGUI()
    app.run()

if __name__ == "__main__":
    main()