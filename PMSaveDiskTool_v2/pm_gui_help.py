"""Help popover and ``?`` trigger button.

Pulled out of ``pm_gui.py`` so Toplevel modules (Byte Workbench, Line-up
Coach, …) can open a help dialog without importing back into the main
module — that would create a circular import.
"""

import tkinter as tk
from tkinter import ttk

from pm_core import help_text

from pm_gui_theme import PAL, _retro


class HelpDialog(tk.Toplevel):
    """Modeless popover that renders a topic from ``pm_core.help_text.HELP``.

    The body uses a lightweight markup: lines starting with ``# `` are
    section headers, ``## `` subsection headers, ``- `` bullets, and blank
    lines are paragraph breaks. Everything is rendered in a styled
    ``tk.Text`` widget sharing the main-window palette.
    """

    def __init__(self, parent, topic: str):
        super().__init__(parent)
        title, body = help_text.get(topic)
        self.title(title)
        self.geometry("620x520")
        self.minsize(480, 360)
        self.configure(bg=PAL["bg"])
        self.transient(parent)

        text = tk.Text(
            self,
            wrap="word",
            bg=PAL["bg"],
            fg=PAL["fg_data"],
            insertbackground=PAL["fg_data"],
            selectbackground=PAL["selected"],
            selectforeground=PAL["fg_white"],
            padx=14,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
            font=_retro(11),
        )
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text.tag_configure("h1", foreground=PAL["fg_title"],
                           font=_retro(13, "bold"),
                           spacing1=10, spacing3=4)
        text.tag_configure("h2", foreground=PAL["fg_title"],
                           font=_retro(11, "bold"),
                           spacing1=6, spacing3=2)
        text.tag_configure("bullet", foreground=PAL["fg_data"],
                           lmargin1=16, lmargin2=32, spacing3=2)
        text.tag_configure("para", foreground=PAL["fg_data"], spacing3=4)

        for line in body.splitlines():
            if line.startswith("# "):
                text.insert("end", line[2:] + "\n", "h1")
            elif line.startswith("## "):
                text.insert("end", line[3:] + "\n", "h2")
            elif line.startswith("- "):
                text.insert("end", "• " + line[2:] + "\n", "bullet")
            elif line.strip() == "":
                text.insert("end", "\n")
            else:
                text.insert("end", line + "\n", "para")

        text.configure(state="disabled")

        close = tk.Button(
            self, text="Close", command=self.destroy,
            bg=PAL["bg_mid"], fg=PAL["fg_data"],
            activebackground=PAL["selected"],
            activeforeground=PAL["fg_white"],
            relief="flat", borderwidth=1,
            font=_retro(10, "bold"),
        )
        close.pack(side=tk.BOTTOM, pady=(0, 8))

        self.bind("<Escape>", lambda e: self.destroy())


def help_button(parent, topic: str) -> tk.Button:
    """Small ``?`` button that opens a ``HelpDialog`` for ``topic``."""
    return tk.Button(
        parent, text="?",
        command=lambda: HelpDialog(parent.winfo_toplevel(), topic),
        bg=PAL["bg_mid"], fg=PAL["fg_data"],
        activebackground=PAL["selected"],
        activeforeground=PAL["fg_white"],
        relief="flat", borderwidth=1,
        font=_retro(11, "bold"),
        width=2, cursor="question_arrow",
    )
