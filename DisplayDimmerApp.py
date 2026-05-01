import json
import os
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox
from screeninfo import get_monitors

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


APP_NAME = "Display Dimmer"
SETTINGS_FILE = "display_dimmer_settings.json"


class DisplayDimmerApp:
    def __init__(self):
        self.control = tk.Tk()
        self.control.title(APP_NAME)
        self.control.geometry("560x520")
        self.control.minsize(560, 520)
        self.control.resizable(False, False)
        self.control.configure(bg="#101114")

        self.monitors = list(get_monitors())
        self.overlay_windows = []
        self.dim_monitor_vars = []
        self.dim_opacity = tk.DoubleVar(value=0.85)
        self.is_dimming = False

        self.settings = self.load_settings()
        self.apply_settings()
        self.configure_styles()
        self.build_ui()
        self.setup_escape_hotkey()

        self.control.bind("<Escape>", lambda event: self.stop_dimming())
        self.control.protocol("WM_DELETE_WINDOW", self.quit_app)

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("TFrame", background="#101114")
        self.style.configure("Card.TFrame", background="#181a20", relief="flat")
        self.style.configure("TLabel", background="#101114", foreground="#f2f2f2", font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background="#101114", foreground="#a8acb3", font=("Segoe UI", 9))
        self.style.configure("Card.TLabel", background="#181a20", foreground="#f2f2f2", font=("Segoe UI", 10))
        self.style.configure("CardMuted.TLabel", background="#181a20", foreground="#a8acb3", font=("Segoe UI", 9))
        self.style.configure("Title.TLabel", background="#101114", foreground="#ffffff", font=("Segoe UI", 21, "bold"))
        self.style.configure("StatusActive.TLabel", background="#181a20", foreground="#7CFF9B", font=("Segoe UI", 10, "bold"))
        self.style.configure("StatusInactive.TLabel", background="#181a20", foreground="#ffcc66", font=("Segoe UI", 10, "bold"))

        self.style.configure("TCheckbutton", background="#181a20", foreground="#f2f2f2", font=("Segoe UI", 10))
        self.style.map("TCheckbutton", background=[("active", "#181a20")], foreground=[("active", "#ffffff")])

        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        self.style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(14, 9))
        self.style.configure("Danger.TButton", font=("Segoe UI", 10), padding=(14, 9))

        self.style.configure("Horizontal.TScale", background="#181a20", troughcolor="#2a2e38")

    def build_ui(self):
        main = ttk.Frame(self.control, padding=22)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x")

        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)

        ttk.Label(title_area, text="Display Dimmer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_area,
            text="Dim selected monitors while keeping your movie display bright.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        self.status_card = ttk.Frame(header, style="Card.TFrame", padding=(14, 10))
        self.status_card.pack(side="right")

        ttk.Label(self.status_card, text="STATUS", style="CardMuted.TLabel").pack(anchor="e")
        self.status_label = ttk.Label(self.status_card, text="READY", style="StatusInactive.TLabel")
        self.status_label.pack(anchor="e")

        monitor_card = ttk.Frame(main, style="Card.TFrame", padding=16)
        monitor_card.pack(fill="x", pady=(22, 14))

        ttk.Label(monitor_card, text="Displays to dim", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            monitor_card,
            text="Check the screens you want darkened. Leave the movie screen unchecked.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(3, 12))

        if not self.monitors:
            ttk.Label(monitor_card, text="No monitors detected.", style="Card.TLabel").pack(anchor="w")
        else:
            saved_dimmed = self.settings.get("dimmed_monitor_indices")

            for i, monitor in enumerate(self.monitors):
                if isinstance(saved_dimmed, list):
                    default_value = i in saved_dimmed
                else:
                    default_value = i != 0

                var = tk.BooleanVar(value=default_value)
                self.dim_monitor_vars.append(var)

                primary_tag = "  • likely primary" if monitor.x == 0 and monitor.y == 0 else ""
                label = f"Display {i + 1} — {monitor.width} × {monitor.height}  |  position X:{monitor.x}, Y:{monitor.y}{primary_tag}"

                ttk.Checkbutton(monitor_card, text=label, variable=var).pack(anchor="w", pady=3)

        opacity_card = ttk.Frame(main, style="Card.TFrame", padding=16)
        opacity_card.pack(fill="x", pady=(0, 14))

        row = ttk.Frame(opacity_card, style="Card.TFrame")
        row.pack(fill="x")

        ttk.Label(row, text="Dim strength", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.opacity_label = ttk.Label(row, text=self.opacity_text(), style="CardMuted.TLabel")
        self.opacity_label.pack(side="right")

        opacity_slider = ttk.Scale(
            opacity_card,
            from_=0.20,
            to=0.98,
            variable=self.dim_opacity,
            command=self.update_opacity_label,
            style="Horizontal.TScale",
        )
        opacity_slider.pack(fill="x", pady=(12, 2))

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(4, 14))

        self.toggle_button = ttk.Button(controls, text="Start Dimming", style="Primary.TButton", command=self.toggle_dimming)
        self.toggle_button.pack(side="left", padx=(0, 8))

        ttk.Button(controls, text="Stop", style="Secondary.TButton", command=self.stop_dimming).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Save Settings", style="Secondary.TButton", command=self.save_settings).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Quit", style="Danger.TButton", command=self.quit_app).pack(side="right")

        hotkey_card = ttk.Frame(main, style="Card.TFrame", padding=16)
        hotkey_card.pack(fill="x")

        ttk.Label(hotkey_card, text="Emergency controls", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            hotkey_card,
            text="Press Esc to immediately remove all dimming overlays. The overlays are click-through, so you can still work through dimmed displays.",
            style="CardMuted.TLabel",
            wraplength=490,
        ).pack(anchor="w", pady=(4, 0))

        hotkey_status = "Global Esc hotkey loaded." if KEYBOARD_AVAILABLE else "Global Esc unavailable; Esc works while the app is focused."
        ttk.Label(hotkey_card, text=hotkey_status, style="CardMuted.TLabel").pack(anchor="w", pady=(8, 0))

    def opacity_text(self):
        return f"{round(self.dim_opacity.get() * 100)}% opacity"

    def apply_settings(self):
        opacity = self.settings.get("opacity")
        if isinstance(opacity, (float, int)):
            self.dim_opacity.set(max(0.20, min(0.98, float(opacity))))

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return {}

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def save_settings(self):
        selected_indices = [i for i, var in enumerate(self.dim_monitor_vars) if var.get()]
        data = {
            "opacity": self.dim_opacity.get(),
            "dimmed_monitor_indices": selected_indices,
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            messagebox.showinfo(APP_NAME, "Settings saved.")
        except Exception as error:
            messagebox.showerror(APP_NAME, f"Could not save settings:\n{error}")

    def update_opacity_label(self, _=None):
        self.opacity_label.config(text=self.opacity_text())
        for overlay in self.overlay_windows:
            try:
                overlay.attributes("-alpha", self.dim_opacity.get())
            except tk.TclError:
                pass

    def setup_escape_hotkey(self):
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.add_hotkey("esc", self.stop_dimming, suppress=False)
            except Exception:
                pass

    def toggle_dimming(self):
        if self.is_dimming:
            self.stop_dimming()
        else:
            self.start_dimming()

    def start_dimming(self):
        self.stop_dimming(show_control=False)

        if not self.monitors:
            messagebox.showerror(APP_NAME, "No monitors were detected.")
            return

        selected_indices = [i for i, var in enumerate(self.dim_monitor_vars) if var.get()]

        if not selected_indices:
            messagebox.showwarning(APP_NAME, "Select at least one display to dim.")
            self.control.deiconify()
            self.control.lift()
            return

        for i in selected_indices:
            monitor = self.monitors[i]

            overlay = tk.Toplevel(self.control)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            overlay.attributes("-alpha", self.dim_opacity.get())
            overlay.configure(bg="black")
            overlay.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
            overlay.bind("<Escape>", lambda event: self.stop_dimming())

            self.make_click_through(overlay)
            overlay.after(100, lambda w=overlay: self.keep_on_top(w))
            self.overlay_windows.append(overlay)

        self.is_dimming = True
        self.set_status(active=True)
        self.control.deiconify()
        self.control.lift()
        self.control.focus_force()

    def make_click_through(self, window):
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080

            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def keep_on_top(self, window):
        try:
            window.attributes("-topmost", True)
            if window.winfo_exists():
                window.after(1000, lambda: self.keep_on_top(window))
        except tk.TclError:
            pass

    def set_status(self, active):
        if active:
            self.status_label.config(text="DIMMING", style="StatusActive.TLabel")
            self.toggle_button.config(text="Stop Dimming")
        else:
            self.status_label.config(text="READY", style="StatusInactive.TLabel")
            self.toggle_button.config(text="Start Dimming")

    def stop_dimming(self, show_control=True):
        for overlay in self.overlay_windows:
            try:
                overlay.destroy()
            except tk.TclError:
                pass

        self.overlay_windows.clear()
        self.is_dimming = False

        try:
            self.set_status(active=False)
        except tk.TclError:
            pass

        if show_control:
            try:
                self.control.deiconify()
                self.control.lift()
                self.control.focus_force()
            except tk.TclError:
                pass

    def quit_app(self):
        self.save_settings_silent()
        self.stop_dimming(show_control=False)
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        self.control.destroy()

    def save_settings_silent(self):
        selected_indices = [i for i, var in enumerate(self.dim_monitor_vars) if var.get()]
        data = {
            "opacity": self.dim_opacity.get(),
            "dimmed_monitor_indices": selected_indices,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
        except Exception:
            pass

    def run(self):
        self.control.mainloop()


if __name__ == "__main__":
    app = DisplayDimmerApp()
    app.run()
