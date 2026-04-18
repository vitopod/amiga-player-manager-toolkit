"""First-run welcome dialog.

Styled after the Player Manager title screen — teal/red/navy palette,
banner strips, and five content boxes covering the essentials a new
user needs on first launch.

Kept in its own module so the main ``pm_gui`` doesn't carry the
first-run UI once the user has dismissed it (which happens on almost
every subsequent launch). Accepts an ``on_dismiss(show_at_next_launch)``
callback so the dialog stays ignorant of the preferences layer.
"""

from typing import Callable
import tkinter as tk

from pm_gui_theme import _retro


class WelcomeDialog(tk.Toplevel):
    """First-run welcome screen styled after the Player Manager title.

    Four content boxes summarise the essentials. A single checkbox
    ("Show this at every launch") defaults to unticked, so dismissing
    the dialog permanently disables it. The user can re-enable the
    screen later via Help → Preferences…
    """

    TEAL  = "#3a7a9a"
    RED   = "#cc3333"
    NAVY  = "#000088"
    WHITE = "#ffffff"

    BOXES = [
        ("OPEN YOUR SAVE DISK",
         "File → Open Save Disk… — browse and edit every player"),
        ("OPTIONAL: OPEN GAME DISK",
         "File → Open Game Disk… — unlocks player names"),
        ("BROWSE, EDIT, SAVE",
         "Pick a VIEW, click a player, tweak, save (makes a .bak first)"),
        ("EXPLORE THE TOOLS MENU",
         "Career Tracker · Compare Players · Line-up Coach · Byte Workbench"),
        ("NEED HELP?",
         "Tap the ? button in any window for in-app guidance"),
    ]

    def __init__(self, parent, on_dismiss: Callable[[bool], None] | None = None):
        super().__init__(parent)
        self._on_dismiss = on_dismiss
        self.title("Welcome")
        self.configure(bg=self.TEAL)
        self.resizable(False, False)
        self.transient(parent)
        self.geometry("640x700")

        self._build_banner("WELCOME", top=True)
        for big, small in self.BOXES:
            self._build_box(big, small)
        self._build_banner("", top=False)   # decorative footer strip

        self._keep_var = tk.BooleanVar(value=False)
        footer = tk.Frame(self, bg=self.TEAL)
        footer.pack(fill=tk.X, padx=18, pady=(10, 6))

        tk.Checkbutton(
            footer, variable=self._keep_var,
            text="Show this at every launch",
            bg=self.TEAL, fg=self.WHITE,
            selectcolor=self.NAVY,
            activebackground=self.TEAL, activeforeground=self.WHITE,
            font=_retro(10, "bold"),
            highlightthickness=0, borderwidth=0,
        ).pack(side=tk.LEFT)

        go_btn = tk.Label(
            footer, text="  OK, LET'S GO  ",
            bg=self.NAVY, fg=self.WHITE,
            font=_retro(12, "bold"),
            padx=16, pady=6,
            borderwidth=1, relief="ridge",
            highlightbackground=self.WHITE, highlightthickness=1,
            cursor="hand2",
        )
        go_btn.bind("<Button-1>", lambda e: self._dismiss())
        go_btn.bind("<Enter>", lambda e: go_btn.configure(bg=self.RED))
        go_btn.bind("<Leave>", lambda e: go_btn.configure(bg=self.NAVY))
        go_btn.pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self._dismiss())
        self.bind("<Escape>", lambda e: self._dismiss())
        self.protocol("WM_DELETE_WINDOW", self._dismiss)

        self.update_idletasks()
        self._center_on(parent)

    def _build_banner(self, label: str, top: bool) -> None:
        band = tk.Frame(self, bg=self.RED,
                        highlightbackground=self.WHITE, highlightthickness=1)
        band.pack(fill=tk.X, padx=18,
                  pady=((18, 6) if top else (10, 4)))
        if label:
            tk.Label(band, text=label, bg=self.RED, fg=self.WHITE,
                     font=_retro(20, "bold"), pady=10).pack(fill=tk.X)
        else:
            tk.Frame(band, bg=self.RED, height=28).pack(fill=tk.X)

    def _build_box(self, big: str, small: str) -> None:
        box = tk.Frame(self, bg=self.NAVY,
                       highlightbackground=self.WHITE, highlightthickness=1)
        box.pack(fill=tk.X, padx=36, pady=6)
        tk.Label(box, text=big,
                 bg=self.NAVY, fg=self.WHITE,
                 font=_retro(14, "bold"),
                 pady=8).pack(fill=tk.X)
        tk.Label(box, text=small,
                 bg=self.NAVY, fg=self.WHITE,
                 font=_retro(10),
                 pady=(0)).pack(fill=tk.X, pady=(0, 8))

    def _center_on(self, parent) -> None:
        parent.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        pw = parent.winfo_width() or self.winfo_screenwidth()
        ph = parent.winfo_height() or self.winfo_screenheight()
        px = parent.winfo_rootx() if parent.winfo_viewable() else 0
        py = parent.winfo_rooty() if parent.winfo_viewable() else 0
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _dismiss(self) -> None:
        if self._on_dismiss is not None:
            self._on_dismiss(bool(self._keep_var.get()))
        self.destroy()
