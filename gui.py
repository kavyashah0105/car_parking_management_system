import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from auth import register_user, login_user
from parking_logic import (
    check_vacancy, get_all_slots, reserve_slot,
    cancel_slot, call_car, pay_annual_fee
)

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0a0d14"
CARD    = "#12151f"
CARD2   = "#1c2030"
INPUT   = "#1e2235"
ACCENT  = "#2d7ef7"
ACCENT2 = "#6c3aed"
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARN    = "#f59e0b"
TEXT    = "#e8edf5"
MUTED   = "#556070"
BORDER  = "#252a3a"

FH1  = ("Segoe UI Semibold", 20)
FH2  = ("Segoe UI Semibold", 13)
FB   = ("Segoe UI", 11)
FSM  = ("Segoe UI", 9)
FBTN = ("Segoe UI Semibold", 10)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.,png.png")


# ── Utility ───────────────────────────────────────────────────────────────────
def _darken(hex_color, factor=0.75):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(int(r*factor), int(g*factor), int(b*factor))


def _accent_btn(parent, text, cmd, bg=ACCENT, width=None):
    kw = dict(text=text, command=cmd, font=FBTN, bg=bg, fg=TEXT,
              activebackground=_darken(bg), activeforeground=TEXT,
              relief="flat", bd=0, cursor="hand2", pady=10)
    if width:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=_darken(bg)))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def _ghost_btn(parent, text, cmd):
    b = tk.Button(parent, text=text, command=cmd, font=FSM,
                  bg=CARD, fg=MUTED, activebackground=CARD,
                  activeforeground=ACCENT, relief="flat", bd=0, cursor="hand2")
    b.bind("<Enter>", lambda e: b.config(fg=ACCENT))
    b.bind("<Leave>", lambda e: b.config(fg=MUTED))
    return b


def _divider(parent, bg=CARD):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=6)


def _label(parent, text, font=FB, fg=TEXT, bg=CARD, anchor="w", **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, anchor=anchor, **kw)


def _make_field(parent, label_text, placeholder="", show="", bg=CARD):
    """
    All-in-one: label + bordered frame + entry with placeholder.
    Entry is created as a direct child of the inner frame — no pack(in_=...).
    Returns (entry_widget, StringVar).
    """
    _label(parent, label_text, font=FSM, fg=MUTED, bg=bg).pack(fill="x", pady=(8, 2))
    border = tk.Frame(parent, bg=BORDER)
    border.pack(fill="x")
    inner = tk.Frame(border, bg=INPUT)
    inner.pack(fill="x", padx=1, pady=1)

    var = tk.StringVar(value=placeholder)
    ent = tk.Entry(inner, textvariable=var, font=FB, fg=MUTED,
                   bg=INPUT, insertbackground=TEXT, relief="flat", bd=0, show=show)
    ent.pack(fill="x", ipady=7, padx=8)

    def _in(_):
        if var.get() == placeholder:
            var.set("")
            ent.config(fg=TEXT, show=show)

    def _out(_):
        if var.get() == "" and placeholder:
            ent.config(show=show, fg=MUTED)
            var.set(placeholder)

    ent.bind("<FocusIn>",  _in)
    ent.bind("<FocusOut>", _out)
    return ent, var


def _pw_field(parent, label="Password", bg=CARD):
    """Password entry with eye toggle. Returns (entry, StringVar)."""
    _label(parent, label, font=FSM, fg=MUTED, bg=bg).pack(fill="x", pady=(8, 2))
    border = tk.Frame(parent, bg=BORDER)
    border.pack(fill="x")
    inner = tk.Frame(border, bg=INPUT)
    inner.pack(fill="x", padx=1, pady=1)

    var = tk.StringVar()
    ent = tk.Entry(inner, textvariable=var, font=FB, bg=INPUT, fg=TEXT,
                   insertbackground=TEXT, relief="flat", bd=0, show="*")
    ent.pack(side="left", fill="x", expand=True, ipady=7, padx=(8, 0))

    visible = tk.BooleanVar(value=False)

    def _toggle():
        visible.set(not visible.get())
        ent.config(show="" if visible.get() else "*")
        eye.config(text="◉" if visible.get() else "◎")

    eye = tk.Button(inner, text="◎", command=_toggle, font=("Segoe UI", 11),
                    bg=INPUT, fg=MUTED, activebackground=INPUT,
                    activeforeground=ACCENT, relief="flat", bd=0,
                    cursor="hand2", padx=8)
    eye.pack(side="right", ipady=7)
    return ent, var


# ── Logo loader ───────────────────────────────────────────────────────────────
def _load_logo(size=(80, 80)):
    try:
        img = Image.open(LOGO_PATH).convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ── App ───────────────────────────────────────────────────────────────────────
class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartPark")
        self.root.geometry("1020x700")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.current_user = None
        self._logo_img = _load_logo((72, 72))
        self._logo_sm  = _load_logo((36, 36))
        self.show_login()

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ── shared helpers ────────────────────────────────────────────────────────
    def _card(self, parent=None, padx=38, pady=32, bg=CARD):
        if parent is None:
            parent = self.root
        outer = tk.Frame(parent, bg=BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        card = tk.Frame(outer, bg=bg, padx=padx, pady=pady)
        card.pack()
        tk.Frame(card, bg=ACCENT, height=3).pack(fill="x", pady=(0, 18))
        return card

    def _logo_header(self, parent, subtitle=""):
        row = tk.Frame(parent, bg=CARD)
        row.pack(pady=(0, 4))
        if self._logo_img:
            tk.Label(row, image=self._logo_img, bg=CARD).pack(side="left", padx=(0, 12))
        tk.Label(row, text="SmartPark", font=("Segoe UI Semibold", 22),
                 fg=TEXT, bg=CARD).pack(side="left", anchor="s", pady=6)
        if subtitle:
            _label(parent, subtitle, font=FSM, fg=MUTED, bg=CARD,
                   anchor="center").pack(fill="x", pady=(0, 14))

    # ── Login ─────────────────────────────────────────────────────────────────
    def show_login(self):
        self.clear()
        card = self._card()
        self._logo_header(card, "Sign in to your account")

        self.l_user_ent, self.l_user_var = _make_field(card, "Username", "Username")
        self.l_pw_ent,   self.l_pw_var   = _pw_field(card, "Password")

        _accent_btn(card, "Sign In", self.login, width=34).pack(fill="x", pady=(18, 6))
        _ghost_btn(card, "No account? Register →", self.show_register).pack(anchor="e")

    def login(self):
        u = self.l_user_var.get().strip()
        p = self.l_pw_var.get().strip()
        if u in ("", "Username") or not p:
            messagebox.showerror("Error", "Please enter your username and password.")
            return
        if login_user(u, p):
            self.current_user = u
            self.show_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    # ── Register ──────────────────────────────────────────────────────────────
    def show_register(self):
        self.clear()

        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview, bg=BG)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((510, 10), window=inner, anchor="n")

        card = tk.Frame(inner, bg=CARD, padx=38, pady=32)
        card.pack(pady=24)
        tk.Frame(card, bg=ACCENT2, height=3).pack(fill="x", pady=(0, 18))

        self._logo_header(card, "Create your account")

        # ── Account section
        _label(card, "ACCOUNT INFO", font=("Segoe UI Semibold", 8),
               fg=ACCENT, bg=CARD).pack(anchor="w", pady=(4, 0))
        _divider(card)

        self.r_user_ent,  self.r_user_var  = _make_field(card, "Username",     "Username")
        self.r_email_ent, self.r_email_var = _make_field(card, "Email",        "Email address")
        self.r_pw_ent,    self.r_pw_var    = _pw_field(card, "Password")

        # ── Vehicle section
        _label(card, "VEHICLE INFO", font=("Segoe UI Semibold", 8),
               fg=ACCENT, bg=CARD).pack(anchor="w", pady=(16, 0))
        _divider(card)

        self.r_plate_ent, self.r_plate_var = _make_field(card, "Number Plate", "e.g. MH12AB1234")
        self.r_brand_ent, self.r_brand_var = _make_field(card, "Car Brand",    "e.g. Toyota")
        self.r_model_ent, self.r_model_var = _make_field(card, "Car Model",    "e.g. Camry")

        _accent_btn(card, "Create Account", self.register,
                    bg=ACCENT2, width=34).pack(fill="x", pady=(20, 6))
        _ghost_btn(card, "Already have an account? Sign in →",
                   self.show_login).pack(anchor="e")

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (1 if e.delta > 0 else -1), "units"))

    def register(self):
        placeholders = {"Username", "Email address", "e.g. MH12AB1234",
                        "e.g. Toyota", "e.g. Camry", ""}
        vals = {
            "username":  self.r_user_var.get().strip(),
            "email":     self.r_email_var.get().strip(),
            "password":  self.r_pw_var.get().strip(),
            "car_no":    self.r_plate_var.get().strip(),
            "car_brand": self.r_brand_var.get().strip(),
            "car_model": self.r_model_var.get().strip(),
        }
        if any(v in placeholders for v in vals.values()):
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        msg = register_user(**vals)
        if "successful" in msg.lower():
            messagebox.showinfo("Success", msg)
            self.show_login()
        else:
            messagebox.showerror("Registration Failed", msg)

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def show_dashboard(self):
        self.clear()
        self.root.configure(bg=BG)

    # ── Top nav
        nav = tk.Frame(self.root, bg=CARD, height=58)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        nav_left = tk.Frame(nav, bg=CARD)
        nav_left.pack(side="left", padx=18, pady=10)
        if self._logo_sm:
         tk.Label(nav_left, image=self._logo_sm, bg=CARD).pack(side="left", padx=(0, 8))

        _label(nav_left, "SmartPark", font=("Segoe UI Semibold", 14),
           fg=TEXT, bg=CARD).pack(side="left")

        nav_right = tk.Frame(nav, bg=CARD)
        nav_right.pack(side="right", padx=18)

        _label(nav_right, f"👤  {self.current_user}", font=FSM,
           fg=MUTED, bg=CARD).pack(side="left", pady=18)

        _ghost_btn(nav_right, "  Logout", self.show_login).pack(side="left", padx=(10, 0), pady=14)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    # ── Body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=20)

    # ── Heading + stats
        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(0, 16))

        _label(top, "Parking Overview", font=FH1, fg=TEXT, bg=BG).pack(
            side="left"
        )

        slots = get_all_slots()
        total_slots = len(slots)

        free = sum(1 for slot in slots if not slot["is_occupied"])
        taken = total_slots - free

        for label, val, color in [
            ("Free", free, SUCCESS), 
            ("Occupied", taken, DANGER)
        ]:
            stat = tk.Frame(top, bg=CARD, padx=18, pady=8)
            stat.pack(side="right", padx=6)

            _label(stat, str(val), font=("Segoe UI Semibold", 20), fg=color, 
                   bg=CARD).pack()

            _label(stat, label, font=FSM, fg=MUTED, bg=CARD).pack()

        # ── Scrollable slot grid
        grid_frame = tk.Frame(body, bg=CARD)
        grid_frame.pack(fill="both", expand=True, pady=(10, 10))

        canvas = tk.Canvas(grid_frame, bg=CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(grid_frame, orient="vertical", command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg=CARD)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, slot in enumerate(slots):
            occupied = slot["is_occupied"]
            color = DANGER if occupied else SUCCESS
            plate = slot["vehicle_plate"] or ""

            cell = tk.Frame(scrollable_frame, bg=color, width=120, height=70)
            cell.pack_propagate(False)
            cell.grid(row=i // 5, column=i % 5, padx=6, pady=6)

            _label(cell, f"#{slot['slot_id']}", font=("Segoe UI Semibold", 11), 
                   fg="white", bg=color, anchor="center").pack(expand=True)

            _label(cell, plate if occupied else "FREE", font=FSM, fg="white", 
                   bg=color, anchor="center").pack(pady=(0, 4))

        # ── Legend
        leg = tk.Frame(body, bg=BG)
        leg.pack(anchor="w", pady=(8, 0))

        for col, lbl in [(SUCCESS, "Available"), (DANGER, "Occupied")]:
            tk.Frame(leg, bg=col, width=11, height=11).pack(side="left")
            _label(leg, f"  {lbl}    ", font=FSM, fg=MUTED, bg=BG
                   ).pack(side="left")

        # ── Action buttons
        _label(body, "Quick Actions", font=FH2, fg=TEXT, bg=BG
               ).pack(anchor="w", pady=(20, 10))

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill="x")

        actions = [
            ("Reserve Slot", ACCENT, self.reserve_screen),
            ("Cancel Slot", DANGER, self.cancel_screen),
            ("Call My Car", "#0ea5e9", self.call_car_screen),
            ("Subscription", ACCENT2, self.subscription_screen),
            ("Payment Receipt", "#10b981", self.receipt_screen),
        ]

        for i, (lbl, col, cmd) in enumerate(actions):
            def make_hover(b, col):
                b.bind("<Enter>", lambda e: b.config(bg=_darken(col)))
                b.bind("<Leave>", lambda e: b.config(bg=col))

            b = tk.Button(
                btn_row,
                text=lbl,
                command=cmd,
                font=FBTN,
                bg=col,
                fg="white",
                activebackground=_darken(col),
                activeforeground="white",
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=14,
                pady=11,
                width=14
            )
            b.grid(row=0, column=i, padx=5)
            make_hover(b, col)

    # ── Reserve screen ────────────────────────────────────────────────────────
    def reserve_screen(self):
        win = self._popup("Reserve a Slot")
        _label(win, "Enter your number plate to reserve the next available slot.",
               font=FSM, fg=MUTED, bg=CARD, anchor="w").pack(fill="x", pady=(0, 10))

        ent, var = _make_field(win, "Number Plate", "e.g. MH12AB1234")

        def _do():
            plate = var.get().strip()
            if plate in ("", "e.g. MH12AB1234"):
                messagebox.showerror("Error", "Enter a number plate.", parent=win)
                return
            msg = reserve_slot(plate)
            messagebox.showinfo("Reserve", msg, parent=win)
            win.destroy()
            self.show_dashboard()

        _accent_btn(win, "Reserve", _do, width=28).pack(fill="x", pady=(14, 0))

    # ── Cancel screen ─────────────────────────────────────────────────────────
    def cancel_screen(self):
        win = self._popup("Cancel / Free a Slot")
        _label(win, "Enter the slot number to free it and generate a receipt.",
               font=FSM, fg=MUTED, bg=CARD, anchor="w").pack(fill="x", pady=(0, 10))

        ent, var = _make_field(win, "Slot Number", "Slot number (1–10)")

        def _do():
            try:
                slot_id = int(var.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid slot number.", parent=win)
                return
            msg = cancel_slot(slot_id)
            messagebox.showinfo("Cancel Slot", msg, parent=win)
            win.destroy()
            self.show_dashboard()

        _accent_btn(win, "Free Slot", _do, bg=DANGER, width=28).pack(fill="x", pady=(14, 0))

    # ── Call car screen ───────────────────────────────────────────────────────
    def call_car_screen(self):
        win = self._popup("Call My Car")
        _label(win, "Enter your slot number and floor to retrieve your car.",
               font=FSM, fg=MUTED, bg=CARD, anchor="w").pack(fill="x", pady=(0, 10))

        slot_ent,  slot_var  = _make_field(win, "Slot Number", "Slot number")
        floor_ent, floor_var = _make_field(win, "Floor", "Floor (default 1)")

        def _do():
            try:
                sid = int(slot_var.get().strip())
                fl_raw = floor_var.get().strip()
                fl = int(fl_raw) if fl_raw not in ("", "Floor (default 1)") else 1
            except ValueError:
                messagebox.showerror("Error", "Enter valid numbers.", parent=win)
                return
            msg = call_car(sid, fl)
            messagebox.showinfo("Call Car", msg, parent=win)
            win.destroy()

        _accent_btn(win, "Call Car", _do, bg="#0ea5e9", width=28).pack(fill="x", pady=(14, 0))

    # ── Subscription screen ───────────────────────────────────────────────────
    def subscription_screen(self):
        win = self._popup("Annual Subscription")
        _label(win, "Pay ₹5,000 for an annual parking subscription.",
               font=FSM, fg=MUTED, bg=CARD, anchor="w").pack(fill="x", pady=(0, 10))

        plate_ent, plate_var = _make_field(win, "Number Plate", "Number plate")

        method_var = tk.StringVar(value="Cash")
        mf = tk.Frame(win, bg=CARD)
        mf.pack(fill="x", pady=(10, 0))
        _label(mf, "Payment Method", font=FSM, fg=MUTED, bg=CARD).pack(anchor="w")
        for m in ["Cash", "Credit Card", "UPI"]:
            tk.Radiobutton(mf, text=m, variable=method_var, value=m,
                           font=FB, bg=CARD, fg=TEXT, selectcolor=CARD2,
                           activebackground=CARD).pack(anchor="w")

        def _do():
            plate = plate_var.get().strip()
            if plate in ("", "Number plate"):
                messagebox.showerror("Error", "Enter a number plate.", parent=win)
                return
            msg = pay_annual_fee(plate, method_var.get())
            messagebox.showinfo("Subscription", msg, parent=win)
            win.destroy()

        _accent_btn(win, "Pay ₹5,000", _do, bg=ACCENT2, width=28).pack(fill="x", pady=(14, 0))

    # ── Receipt screen ────────────────────────────────────────────────────────
    def receipt_screen(self):
        win = self._popup("Payment Receipts")
        _label(win, "Recent receipts will appear here once slots are cancelled.",
               font=FSM, fg=MUTED, bg=CARD, anchor="w").pack(fill="x", pady=(0, 6))
        _label(win, "No receipts yet.", font=FB, fg=MUTED, bg=CARD,
               anchor="center").pack(fill="x", pady=20)

    # ── Popup helper ──────────────────────────────────────────────────────────
    def _popup(self, title):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=CARD)
        win.resizable(False, False)
        win.grab_set()
        tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")
        inner = tk.Frame(win, bg=CARD, padx=30, pady=24)
        inner.pack()
        _label(inner, title, font=FH2, fg=TEXT, bg=CARD).pack(anchor="w", pady=(0, 4))
        return inner


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ParkingApp(root)
    root.mainloop()
