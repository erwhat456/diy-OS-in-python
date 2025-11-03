#!/usr/bin/env python3
"""
CinnaOS - Windows 98 Retro Desktop - Full Edition (customized)

Configuration used:
 - Desktop size: 1024x768
 - Startup sound: D:\CinnaOS\windows 98 start.wav
 - Shutdown sound: D:\CinnaOS\tada.wav
 - Recycle bin persisted at: D:\CinnaOS\recycle_bin\

Dependencies:
 - Required: psutil
 - Optional: gputil, matplotlib, simpleaudio

Save as: cinnaos_win98_full.py
Run: python cinnaos_win98_full.py
"""

# Use D:\CinnaOS for persistent storage and sounds per your message.
# you can change it to C:/ if you want to really want to use it as a os.
# but you can use this a CinnaOS to go like windows to go but CinnaOS.

import os
import sys
import time
import threading
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import tkinter.scrolledtext as scrolled

# --- External libraries (optional/required) ---
try:
    import psutil
except Exception:
    print("psutil is required. Install: pip install psutil")
    raise

try:
    import GPUtil
    GPUtil_available = True
except Exception:
    GPUtil_available = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# sound backends
SOUND_BACKENDS = {}
try:
    import winsound
    SOUND_BACKENDS["winsound"] = winsound
except Exception:
    winsound = None
try:
    import simpleaudio as sa
    SOUND_BACKENDS["simpleaudio"] = sa
except Exception:
    sa = None

# --- Config (user choices applied) ---
WINDOW_W = 1024
WINDOW_H = 768

# Use D:\CinnaOS for persistent storage and sounds per your message.
# you can change it to C:/ if you want to really want to use it as a os.
# but you can use this a CinnaOS to go like windows to go but CinnaOS.

BASE_FOLDER = Path("D:/CinnaOS")
RECYCLE_DIR = BASE_FOLDER / "recycle_bin"
RECYCLE_INDEX = RECYCLE_DIR / "index.json"

# Sound files (per your choice)
STARTUP_WAV = BASE_FOLDER / "windows 98 start.wav"
SHUTDOWN_WAV = BASE_FOLDER / "tada.wav"

# GUI theme (retro)
THEME_BG = "#c0d7ff"      # retro-blue desktop bg
WIN98_BG = "#c0c0c0"
WIN98_PANEL = "#e0e0e0"
BTN_BG = "#d4d0c8"
BTN_ACTIVE = "#bdbdbd"
FONT = ("MS Sans Serif", 10)
TITLE_FONT = ("MS Sans Serif", 10, "bold")

# Ensure folders exist
RECYCLE_DIR.mkdir(parents=True, exist_ok=True)
if not RECYCLE_INDEX.exists():
    RECYCLE_INDEX.write_text(json.dumps({}), encoding="utf-8")


# ---------- Helpers ----------
def play_sound(path: Path):
    """Non-fatal attempt to play a WAV file asynchronously."""
    if not path.exists():
        return
    try:
        if "winsound" in SOUND_BACKENDS:
            SOUND_BACKENDS["winsound"].PlaySound(str(path), SOUND_BACKENDS["winsound"].SND_FILENAME | SOUND_BACKENDS["winsound"].SND_ASYNC)
            return
    except Exception:
        pass
    try:
        if "simpleaudio" in SOUND_BACKENDS:
            wave_obj = SOUND_BACKENDS["simpleaudio"].WaveObject.from_wave_file(str(path))
            wave_obj.play()
            return
    except Exception:
        pass
    # fallback: no-op


def format_bytes(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def is_ethernet_connected():
    """Return (bool, interface_name_or_None). Heuristic based on interface names / speed."""
    try:
        stats = psutil.net_if_stats()
        for name, st in stats.items():
            if not st.isup:
                continue
            lname = name.lower()
            if lname.startswith("lo") or "loop" in lname:
                continue
            if any(x in lname for x in ("eth", "ethernet", "en")):
                return True, name
            if st.speed and st.speed > 0:
                return True, name
        # fallback
        for name, st in stats.items():
            if st.isup and not name.lower().startswith("lo"):
                return True, name
    except Exception:
        pass
    return False, None


# ---------- Recycle Bin persistence ----------
def load_recycle_index():
    try:
        return json.loads(RECYCLE_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_recycle_index(idx):
    try:
        RECYCLE_INDEX.write_text(json.dumps(idx), encoding="utf-8")
    except Exception:
        pass


def move_to_recycle(path: str):
    """
    Move a real file into recycle archive (copy bytes into recycle_dir),
    remove original if possible, and record meta in index.json.
    Returns key.
    """
    idx = load_recycle_index()
    name = os.path.basename(path) or "unknown"
    timestamp = int(time.time())
    key = f"{timestamp}_{name}"
    target = RECYCLE_DIR / key
    try:
        if os.path.isfile(path):
            with open(path, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
            try:
                os.remove(path)
            except Exception:
                pass
            idx[key] = {"orig": os.path.abspath(path), "type": "file", "saved": str(target)}
        else:
            idx[key] = {"orig": os.path.abspath(path), "type": "unknown", "saved": None}
    except Exception:
        idx[key] = {"orig": os.path.abspath(path), "type": "error", "saved": None}
    save_recycle_index(idx)
    return key


def restore_from_recycle(key: str, target_path: str = None):
    idx = load_recycle_index()
    if key not in idx:
        return False, "Not found"
    entry = idx[key]
    try:
        if entry.get("saved"):
            saved = Path(entry["saved"])
            dest = Path(target_path) if target_path else Path(entry["orig"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(saved, "rb") as s, open(dest, "wb") as d:
                d.write(s.read())
        # remove saved file if exists
        if entry.get("saved"):
            try:
                Path(entry["saved"]).unlink()
            except Exception:
                pass
        idx.pop(key, None)
        save_recycle_index(idx)
        return True, "Restored"
    except Exception as e:
        return False, str(e)


def empty_recycle():
    idx = load_recycle_index()
    for k, v in idx.items():
        if v.get("saved"):
            try:
                Path(v["saved"]).unlink()
            except Exception:
                pass
    save_recycle_index({})
    return True


# ---------- Splash screens ----------
class BootSplash(tk.Toplevel):
    def __init__(self, master, on_done=None):
        super().__init__(master)
        self.on_done = on_done
        self.overrideredirect(True)
        self.configure(bg="black")
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        w = 640; h = 320
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        lbl = tk.Label(self, text="CinnaOS", fg="#a6e1ff", bg="black", font=("MS Sans Serif", 36, "bold"))
        lbl.pack(expand=True)
        self.progress = ttk.Progressbar(self, length=500, mode="determinate")
        self.progress.pack(pady=20)
        self.after(50, self._start)

    def _start(self):
        threading.Thread(target=play_sound, args=(STARTUP_WAV,), daemon=True).start()
        for i in range(101):
            self.progress['value'] = i
            self.update_idletasks()
            time.sleep(0.015 + i * 0.0002)
        self.destroy()
        if callable(self.on_done):
            self.on_done()


class ShutdownSplash(tk.Toplevel):
    def __init__(self, master, on_done=None):
        super().__init__(master)
        self.on_done = on_done
        self.overrideredirect(True)
        self.configure(bg="black")
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        w = 480; h = 220
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        lbl = tk.Label(self, text="Shutting down CinnaOS...", fg="#ffd1a6", bg="black", font=("MS Sans Serif", 18))
        lbl.pack(expand=True)
        self.after(50, self._start)

    def _start(self):
        threading.Thread(target=play_sound, args=(SHUTDOWN_WAV,), daemon=True).start()
        for i in range(50):
            time.sleep(0.02)
            self.update_idletasks()
        self.destroy()
        if callable(self.on_done):
            self.on_done()


# ---------- Desktop shell ----------
class CinnaDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CinnaOS - Windows 98 Edition")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.configure(bg=THEME_BG)
        self.protocol("WM_DELETE_WINDOW", self.request_shutdown)
        self._stop = False
        self.task_buttons = []
        self.desktop_icons = []
        self.start_menu = None
        self._create_ui()
        self.after(1000, self._update_status)
        self.center_window()

    def center_window(self):
        ws = self.winfo_screenwidth(); hs = self.winfo_screenheight()
        x = (ws - WINDOW_W) // 2; y = (hs - WINDOW_H) // 2
        self.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

    def _create_ui(self):
        self.desktop_frame = tk.Frame(self, bg=THEME_BG)
        self.desktop_frame.pack(fill="both", expand=True)
        self._create_icons()
        self.taskbar = tk.Frame(self, bg=WIN98_PANEL, height=36, bd=2, relief="raised")
        self.taskbar.pack(side="bottom", fill="x")
        self.start_btn = tk.Button(self.taskbar, text="Start", bg=BTN_BG, relief="raised", command=self.toggle_start_menu)
        self.start_btn.pack(side="left", padx=4, pady=4)
        self.taskframe = tk.Frame(self.taskbar, bg=WIN98_PANEL)
        self.taskframe.pack(side="left", padx=6)
        self.status_frame = tk.Frame(self.taskbar, bg=WIN98_PANEL)
        self.status_frame.pack(side="right", padx=6)
        self.eth_label = tk.Label(self.status_frame, text="Ethernet: —", bg=WIN98_PANEL, font=("Consolas", 9))
        self.eth_label.pack(side="right", padx=6)
        self.clock_label = tk.Label(self.status_frame, text="", bg=WIN98_PANEL, font=("Consolas", 9))
        self.clock_label.pack(side="right", padx=6)
        self.desktop_frame.bind("<Button-3>", self._desktop_right_click)

    def _create_icons(self):
        icons = [
            ("My Computer", self.open_my_computer),
            ("File Explorer", self.open_file_explorer),
            ("Notepad", self.open_notepad),
            ("Paint", self.open_paint),
            ("Calculator", self.open_calculator),
            ("Control Panel", self.open_control_panel),
            ("Task Manager", self.open_task_manager),
            ("Recycle Bin", self.open_recycle_bin),
        ]
        x = 20; y = 20
        for name, cmd in icons:
            frame = tk.Frame(self.desktop_frame, width=96, height=96, bg=THEME_BG)
            frame.place(x=x, y=y)
            icon_lbl = tk.Label(frame, text="🗋", bg=THEME_BG, font=("Segoe UI", 22))
            icon_lbl.pack()
            btn = tk.Button(frame, text=name, bg=THEME_BG, relief="flat", command=cmd)
            btn.pack()
            btn.bind("<Button-3>", lambda e, nm=name, fn=cmd: self._icon_context_menu(e, nm, fn))
            btn.bind("<Double-Button-1>", lambda e, fn=cmd: fn())
            self.desktop_icons.append((frame, name))
            y += 100
            if y > WINDOW_H - 200:
                y = 20; x += 110

    def _desktop_right_click(self, ev):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="New -> Folder", command=lambda: self._create_new_folder())
        menu.add_command(label="Refresh", command=lambda: None)
        menu.add_separator()
        menu.add_command(label="Properties", command=lambda: messagebox.showinfo("Desktop Properties", "CinnaOS Desktop\nRetro theme"))
        menu.tk_popup(ev.x_root, ev.y_root)

    def _icon_context_menu(self, ev, name, func):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"Open {name}", command=func)
        if name == "Recycle Bin":
            menu.add_command(label="Empty Recycle Bin", command=lambda: (empty_recycle(), messagebox.showinfo("Recycle", "Emptied")))
        else:
            menu.add_command(label="Delete", command=lambda: self._delete_icon_item(name))
        menu.add_command(label="Properties", command=lambda: messagebox.showinfo("Properties", f"{name} properties"))
        menu.tk_popup(ev.x_root, ev.y_root)

    def _create_new_folder(self):
        name = f"NewFolder_{int(time.time())}"
        p = Path.cwd() / name
        try:
            p.mkdir(exist_ok=True)
            messagebox.showinfo("New Folder", f"Created {p}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_icon_item(self, name):
        target = filedialog.askopenfilename(title=f"Select file to delete (for {name})")
        if target:
            key = move_to_recycle(target)
            messagebox.showinfo("Recycle", f"Moved to Recycle Bin: {key}")

    def toggle_start_menu(self):
        if self.start_menu and tk.Toplevel.winfo_exists(self.start_menu):
            self.start_menu.destroy(); self.start_menu = None; return
        w = tk.Toplevel(self)
        w.overrideredirect(True); w.configure(bg=WIN98_PANEL, bd=2, relief="raised")
        bx = self.start_btn.winfo_rootx(); by = self.start_btn.winfo_rooty() - 280
        if by < 0: by = self.start_btn.winfo_rooty() - 120
        w.geometry(f"220x280+{bx}+{by}")
        tk.Label(w, text="CinnaOS Programs", bg=WIN98_PANEL, font=TITLE_FONT).pack(fill="x", padx=6, pady=6)
        frame = tk.Frame(w, bg=WIN98_PANEL); frame.pack(fill="both", expand=True)
        programs = [
            ("Task Manager", self.open_task_manager),
            ("Control Panel", self.open_control_panel),
            ("File Explorer", self.open_file_explorer),
            ("Notepad", self.open_notepad),
            ("Paint", self.open_paint),
            ("Calculator", self.open_calculator),
            ("Shutdown", self.request_shutdown),
        ]
        for pname, pfunc in programs:
            b = tk.Button(frame, text=pname, bg=BTN_BG, relief="raised", command=lambda f=pfunc, w=w: (f(), w.destroy()))
            b.pack(fill="x", padx=6, pady=4)
        self.start_menu = w

    def add_task_button(self, title, winref):
        for t, ref in self.task_buttons:
            if t == title: return
        b = tk.Button(self.taskframe, text=title, bg=BTN_BG, relief="raised", command=lambda r=winref: r.lift())
        b.pack(side="left", padx=2)
        self.task_buttons.append((title, winref))

    def remove_task_button(self, title):
        for i, (t, ref) in enumerate(list(self.task_buttons)):
            if t == title:
                self.task_buttons.pop(i)
                break
        for child in self.taskframe.winfo_children():
            child.destroy()
        for t, ref in self.task_buttons:
            b = tk.Button(self.taskframe, text=t, bg=BTN_BG, relief="raised", command=lambda r=ref: r.lift())
            b.pack(side="left", padx=2)

    def _update_status(self):
        eth, name = is_ethernet_connected()
        self.eth_label.config(text=f"Ethernet: {'Yes ('+name+')' if eth else 'No'}")
        self.clock_label.config(text=time.strftime("%Y-%m-%d %H:%M:%S"))
        if not self._stop:
            self.after(1000, self._update_status)

    # App openers
    def open_notepad(self):
        win = AppWindow(self, "Notepad", 640, 480)
        NotepadApp(win)
        self.add_task_button("Notepad", win)

    def open_paint(self):
        win = AppWindow(self, "Paint", 700, 520)
        PaintApp(win)
        self.add_task_button("Paint", win)

    def open_file_explorer(self):
        win = AppWindow(self, "File Explorer", 720, 480)
        FileExplorerApp(win)
        self.add_task_button("File Explorer", win)

    def open_calculator(self):
        win = AppWindow(self, "Calculator", 320, 420)
        CalculatorApp(win)
        self.add_task_button("Calculator", win)

    def open_control_panel(self):
        win = AppWindow(self, "Control Panel", 520, 440)
        ControlPanelApp(win)
        self.add_task_button("Control Panel", win)

    def open_task_manager(self):
        win = AppWindow(self, "Task Manager", 620, 440)
        TaskManagerApp(win)
        self.add_task_button("Task Manager", win)

    def open_recycle_bin(self):
        win = AppWindow(self, "Recycle Bin", 520, 420)
        RecycleBinApp(win)
        self.add_task_button("Recycle Bin", win)

    def open_my_computer(self):
        win = AppWindow(self, "My Computer", 520, 360)
        MyComputerApp(win)
        self.add_task_button("My Computer", win)

    def request_shutdown(self):
        if messagebox.askyesno("Shutdown", "Are you sure you want to shut down CinnaOS?"):
            def _do():
                s = ShutdownSplash(self)
                time.sleep(1.2)
                try:
                    self._stop = True
                    self.destroy()
                except Exception:
                    os._exit(0)
            threading.Thread(target=_do, daemon=True).start()


# ---------- Generic App Window ----------
class AppWindow(tk.Toplevel):
    def __init__(self, parent, title, w, h):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry(f"{w}x{h}")
        self.configure(bg=WIN98_PANEL)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.content = tk.Frame(self, bg=WIN98_PANEL)
        self.content.pack(fill="both", expand=True)
        threading.Thread(target=play_sound, args=(STARTUP_WAV,), daemon=True).start()

    def _on_close(self):
        threading.Thread(target=play_sound, args=(SHUTDOWN_WAV,), daemon=True).start()
        try:
            self.destroy()
        except Exception:
            pass


# ---------- Notepad ----------
class NotepadApp:
    def __init__(self, win: AppWindow):
        self.win = win
        toolbar = tk.Frame(win.content, bg=WIN98_PANEL)
        toolbar.pack(fill="x", padx=6, pady=6)
        tk.Button(toolbar, text="Open", command=self.open_file, bg=BTN_BG).pack(side="left", padx=4)
        tk.Button(toolbar, text="Save", command=self.save_file, bg=BTN_BG).pack(side="left", padx=4)
        tk.Button(toolbar, text="Save As", command=self.save_as, bg=BTN_BG).pack(side="left", padx=4)
        self.text = scrolled.ScrolledText(win.content, font=("Consolas", 11))
        self.text.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.current = None

    def open_file(self):
        p = filedialog.askopenfilename()
        if p:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    self.text.delete("1.0", "end"); self.text.insert("1.0", f.read())
                self.current = p
                self.win.title(f"Notepad - {os.path.basename(p)}")
            except Exception as e:
                messagebox.showerror("Open", str(e))

    def save_file(self):
        if self.current:
            try:
                with open(self.current, "w", encoding="utf-8") as f:
                    f.write(self.text.get("1.0", "end"))
                messagebox.showinfo("Saved", "Saved.")
            except Exception as e:
                messagebox.showerror("Save", str(e))
        else:
            self.save_as()

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt")
        if p:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(self.text.get("1.0", "end"))
                self.current = p
                self.win.title(f"Notepad - {os.path.basename(p)}")
            except Exception as e:
                messagebox.showerror("Save", str(e))


# ---------- Paint ----------
class PaintApp:
    def __init__(self, win: AppWindow):
        self.win = win
        tb = tk.Frame(win.content, bg=WIN98_PANEL); tb.pack(fill="x", padx=6, pady=6)
        self.color = "#000000"; self.brush = tk.IntVar(value=4)
        tk.Button(tb, text="Color", command=self.choose_color, bg=BTN_BG).pack(side="left", padx=4)
        tk.Label(tb, text="Brush:", bg=WIN98_PANEL).pack(side="left", padx=6)
        tk.Spinbox(tb, from_=1, to=50, textvariable=self.brush, width=4).pack(side="left")
        tk.Button(tb, text="Save", command=self.save, bg=BTN_BG).pack(side="left", padx=6)
        tk.Button(tb, text="Clear", command=self.clear, bg=BTN_BG).pack(side="left", padx=6)
        self.canvas = tk.Canvas(win.content, bg="white", cursor="cross")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.canvas.bind("<B1-Motion>", self.paint)

    def choose_color(self):
        c = colorchooser.askcolor()[1]
        if c: self.color = c

    def paint(self, e):
        r = int(self.brush.get()); x, y = e.x, e.y
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=self.color, outline=self.color)

    def save(self):
        p = filedialog.asksaveasfilename(defaultextension=".ps")
        if p:
            try:
                self.canvas.postscript(file=p); messagebox.showinfo("Saved", "Saved PS.")
            except Exception as e:
                messagebox.showerror("Save", str(e))

    def clear(self): self.canvas.delete("all")


# ---------- File Explorer ----------
class FileExplorerApp:
    def __init__(self, win: AppWindow):
        self.win = win
        top = tk.Frame(win.content, bg=WIN98_PANEL); top.pack(fill="x", padx=6, pady=6)
        tk.Label(top, text="Path:", bg=WIN98_PANEL).pack(side="left")
        self.path_var = tk.StringVar(value=os.path.expanduser("~"))
        tk.Entry(top, textvariable=self.path_var, width=60).pack(side="left", padx=6)
        tk.Button(top, text="Go", command=self.refresh, bg=BTN_BG).pack(side="left")
        self.listbox = tk.Listbox(win.content)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.listbox.bind("<Double-Button-1>", self.open_item)
        self.refresh()

    def refresh(self):
        p = self.path_var.get()
        try:
            items = os.listdir(p)
            self.listbox.delete(0, "end"); self.listbox.insert("end", "..")
            for it in items:
                self.listbox.insert("end", it)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_item(self, ev):
        sel = self.listbox.get(self.listbox.curselection())
        p = self.path_var.get()
        if sel == "..":
            parent = os.path.dirname(p); self.path_var.set(parent or "/"); self.refresh(); return
        new = os.path.join(p, sel)
        if os.path.isdir(new):
            self.path_var.set(new); self.refresh()
        else:
            try:
                if sys.platform.startswith("win"):
                    os.startfile(new)
                else:
                    if os.system(f'xdg-open "{new}"') != 0:
                        os.system(f'open "{new}"')
            except Exception as e:
                messagebox.showerror("Open", str(e))


# ---------- Calculator ----------
class CalculatorApp:
    def __init__(self, win: AppWindow):
        self.win = win
        self.entry = tk.Entry(win.content, font=("Consolas", 16), justify="right")
        self.entry.pack(fill="x", padx=6, pady=6)
        buttons = [
            ["7","8","9","/"],
            ["4","5","6","*"],
            ["1","2","3","-"],
            ["0",".","=","+"],
        ]
        for row in buttons:
            r = tk.Frame(win.content, bg=WIN98_PANEL); r.pack(fill="x", padx=6)
            for ch in row:
                b = tk.Button(r, text=ch, bg=BTN_BG, command=lambda c=ch: self.on_press(c))
                b.pack(side="left", padx=4, pady=4)

    def on_press(self, ch):
        if ch == "=":
            try:
                val = eval(self.entry.get())
                self.entry.delete(0, "end"); self.entry.insert("end", str(val))
            except Exception:
                self.entry.delete(0, "end"); self.entry.insert("end", "Error")
        else:
            self.entry.insert("end", ch)


# ---------- Recycle Bin App ----------
class RecycleBinApp:
    def __init__(self, win: AppWindow):
        self.win = win
        top = tk.Frame(win.content, bg=WIN98_PANEL); top.pack(fill="x", padx=6, pady=6)
        tk.Button(top, text="Empty Recycle Bin", command=self.empty_bin, bg=BTN_BG).pack(side="left", padx=4)
        tk.Button(top, text="Restore Selected", command=self.restore_selected, bg=BTN_BG).pack(side="left", padx=4)
        self.listbox = tk.Listbox(win.content)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, "end")
        idx = load_recycle_index()
        for k, v in idx.items():
            self.listbox.insert("end", f"{k} — {v.get('orig')}")

    def empty_bin(self):
        if messagebox.askyesno("Empty", "Permanently delete all items?"):
            empty_recycle(); self.refresh(); messagebox.showinfo("Empty", "Recycle Bin emptied.")

    def restore_selected(self):
        try:
            sel = self.listbox.get(self.listbox.curselection())
        except Exception:
            messagebox.showinfo("Select", "Select an item first."); return
        key = sel.split(" — ")[0]
        ok, msg = restore_from_recycle(key)
        if ok:
            messagebox.showinfo("Restore", "Restored.")
            self.refresh()
        else:
            messagebox.showerror("Restore", msg)


# ---------- Control Panel ----------
class ControlPanelApp:
    def __init__(self, win: AppWindow):
        self.win = win
        left = tk.Frame(win.content, bg=WIN98_PANEL); left.pack(side="left", fill="y", padx=6, pady=6)
        right = tk.Frame(win.content, bg=WIN98_PANEL); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        tk.Button(left, text="System Info", bg=BTN_BG, command=lambda: self.show_info(right)).pack(fill="x", pady=4)
        tk.Button(left, text="Appearance", bg=BTN_BG, command=lambda: self.show_appearance(right)).pack(fill="x", pady=4)
        tk.Button(left, text="Network", bg=BTN_BG, command=lambda: self.show_network(right)).pack(fill="x", pady=4)
        tk.Button(left, text="About", bg=BTN_BG, command=lambda: self.show_about(right)).pack(fill="x", pady=4)
        self.show_info(right)

    def clear(self, right):
        for c in right.winfo_children(): c.destroy()

    def show_info(self, right):
        self.clear(right)
        tk.Label(right, text="System Information", bg=WIN98_PANEL, font=TITLE_FONT).pack(anchor="w")
        tk.Label(right, text=f"Platform: {sys.platform}", bg=WIN98_PANEL).pack(anchor="w")
        tk.Label(right, text=f"CPU cores (logical): {psutil.cpu_count()}", bg=WIN98_PANEL).pack(anchor="w")
        tk.Label(right, text=f"Total RAM: {format_bytes(psutil.virtual_memory().total)}", bg=WIN98_PANEL).pack(anchor="w")
        if GPUtil_available:
            try:
                gpus = GPUtil.getGPUs()
                for g in gpus:
                    tk.Label(right, text=f"GPU: {g.name}", bg=WIN98_PANEL).pack(anchor="w")
            except Exception:
                pass

    def show_appearance(self, right):
        self.clear(right)
        tk.Label(right, text="Appearance", bg=WIN98_PANEL, font=TITLE_FONT).pack(anchor="w")
        tk.Button(right, text="Choose Background Color", bg=BTN_BG, command=self.pick_bg).pack(anchor="w", pady=6)

    def pick_bg(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.win.master.desktop_frame.configure(bg=c)

    def show_network(self, right):
        self.clear(right)
        tk.Label(right, text="Network Interfaces", bg=WIN98_PANEL, font=TITLE_FONT).pack(anchor="w")
        stats = psutil.net_if_stats(); addrs = psutil.net_if_addrs()
        for name, st in stats.items():
            tk.Label(right, text=f"{name} - {'up' if st.isup else 'down'} - {st.speed} Mbps", bg=WIN98_PANEL).pack(anchor="w")
            if name in addrs:
                for a in addrs[name]:
                    tk.Label(right, text=f"   {a.family.name}: {a.address}", bg=WIN98_PANEL).pack(anchor="w")

    def show_about(self, right):
        self.clear(right)
        tk.Label(right, text="About CinnaOS", bg=WIN98_PANEL, font=TITLE_FONT).pack(anchor="w")
        tk.Label(right, text="CinnaOS - Windows98 Retro (Python/Tkinter)", bg=WIN98_PANEL).pack(anchor="w")
        tk.Label(right, text=f"Startup sound: {STARTUP_WAV}", bg=WIN98_PANEL).pack(anchor="w")
        tk.Label(right, text=f"Shutdown sound: {SHUTDOWN_WAV}", bg=WIN98_PANEL).pack(anchor="w")


# ---------- Task Manager ----------
class TaskManagerApp:
    def __init__(self, win: AppWindow):
        self.win = win
        top = tk.Frame(win.content, bg=WIN98_PANEL); top.pack(fill="x", padx=6, pady=6)
        tk.Button(top, text="Performance", bg=BTN_BG, command=self.show_perf).pack(side="left", padx=4)
        tk.Button(top, text="Network", bg=BTN_BG, command=self.show_net).pack(side="left", padx=4)
        self.body = tk.Frame(win.content, bg=WIN98_PANEL); self.body.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.prev_net = psutil.net_io_counters()
        self._running = True
        self.show_perf()
        threading.Thread(target=self._loop, daemon=True).start()

    def show_perf(self):
        for c in self.body.winfo_children(): c.destroy()
        self.cpu_label = tk.Label(self.body, text="CPU: -- %", bg=WIN98_PANEL); self.cpu_label.pack(anchor="w", pady=4)
        self.ram_label = tk.Label(self.body, text="RAM: -- %", bg=WIN98_PANEL); self.ram_label.pack(anchor="w", pady=4)
        self.disk_label = tk.Label(self.body, text="Disk: -- %", bg=WIN98_PANEL); self.disk_label.pack(anchor="w", pady=4)
        self.gpu_label = tk.Label(self.body, text="GPU: N/A", bg=WIN98_PANEL); self.gpu_label.pack(anchor="w", pady=4)
        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(5, 2), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_ylim(0, 100)
            self.ax.set_title("CPU usage (last 60s)")
            self.line, = self.ax.plot([], [])
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.body)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.cpu_history = [0] * 60
        else:
            self.cpu_bar = ttk.Progressbar(self.body, length=300)
            self.cpu_bar.pack(pady=4)
            self.ram_bar = ttk.Progressbar(self.body, length=300)
            self.ram_bar.pack(pady=4)

    def show_net(self):
        for c in self.body.winfo_children(): c.destroy()
        tk.Label(self.body, text="Network Interfaces and rates", bg=WIN98_PANEL).pack(anchor="w")
        self.net_list = tk.Listbox(self.body)
        self.net_list.pack(fill="both", expand=True)
        self._populate_net()

    def _populate_net(self):
        self.net_list.delete(0, "end")
        stats = psutil.net_if_stats(); addrs = psutil.net_if_addrs()
        for name, st in stats.items():
            self.net_list.insert("end", f"{name}: {'up' if st.isup else 'down'} - speed {st.speed}")
            if name in addrs:
                for a in addrs[name]:
                    self.net_list.insert("end", f"   {a.family.name} {a.address}")

    def _loop(self):
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                net = psutil.net_io_counters()
                up = (net.bytes_sent - self.prev_net.bytes_sent) / 1024.0
                down = (net.bytes_recv - self.prev_net.bytes_recv) / 1024.0
                self.prev_net = net
                gpu_text = "N/A"
                if GPUtil_available:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            g = gpus[0]
                            gpu_text = f"{g.name} - {g.load*100:.1f}%"
                    except Exception:
                        pass

                def upd():
                    try:
                        self.cpu_label.config(text=f"CPU: {cpu:.1f}%")
                        self.ram_label.config(text=f"RAM: {ram:.1f}%")
                        self.disk_label.config(text=f"Disk: {disk:.1f}%")
                        self.gpu_label.config(text=f"GPU: {gpu_text}")
                        if MATPLOTLIB_AVAILABLE:
                            self.cpu_history.append(cpu); self.cpu_history.pop(0)
                            self.line.set_data(range(len(self.cpu_history)), self.cpu_history)
                            self.ax.set_xlim(0, len(self.cpu_history))
                            self.canvas.draw()
                        else:
                            try:
                                self.cpu_bar['value'] = cpu
                                self.ram_bar['value'] = ram
                            except Exception:
                                pass
                    except Exception:
                        pass

                try:
                    self.win.after(0, upd)
                except Exception:
                    upd()
            except Exception:
                time.sleep(1)


# ---------- My Computer ----------
class MyComputerApp:
    def __init__(self, win: AppWindow):
        self.win = win
        tk.Label(win.content, text="Drives", bg=WIN98_PANEL, font=TITLE_FONT).pack(anchor="w", padx=6, pady=6)
        frame = tk.Frame(win.content, bg=WIN98_PANEL); frame.pack(fill="both", expand=True, padx=6, pady=6)
        parts = psutil.disk_partitions(all=False)
        for p in parts:
            try:
                u = psutil.disk_usage(p.mountpoint)
                tk.Label(frame, text=f"{p.device} mounted on {p.mountpoint} - {u.percent:.1f}% used ({format_bytes(u.used)}/{format_bytes(u.total)})", bg=WIN98_PANEL).pack(anchor="w")
            except Exception as e:
                tk.Label(frame, text=f"{p.device} - {e}", bg=WIN98_PANEL).pack(anchor="w")


# ---------- AppWindow & helpers ----------
def center_window(win):
    ws = win.winfo_screenwidth(); hs = win.winfo_screenheight()
    try:
        geom = win.geometry().split("+")[0]
        ww, hh = [int(x) for x in geom.split("x")]
    except Exception:
        ww, hh = 600, 400
    x = (ws - ww) // 2; y = (hs - hh) // 2
    win.geometry(f"{ww}x{hh}+{x}+{y}")


class AppWindow(tk.Toplevel):
    def __init__(self, parent, title, w, h):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry(f"{w}x{h}")
        self.configure(bg=WIN98_PANEL)
        center_window(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.content = tk.Frame(self, bg=WIN98_PANEL)
        self.content.pack(fill="both", expand=True)
        threading.Thread(target=play_sound, args=(STARTUP_WAV,), daemon=True).start()

    def _on_close(self):
        threading.Thread(target=play_sound, args=(SHUTDOWN_WAV,), daemon=True).start()
        try:
            self.destroy()
        except Exception:
            pass


# ---------- Main entry ----------
def main():
    root = tk.Tk()
    root.withdraw()
    def show_desktop():
        root.destroy()
        desktop = CinnaDesktop()
        desktop.mainloop()
    splash = BootSplash(root, on_done=show_desktop)
    splash.mainloop()


if __name__ == "__main__":
    main()
