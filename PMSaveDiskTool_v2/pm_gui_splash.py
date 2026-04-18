"""Splash screen shown briefly on launch.

Opens a borderless Toplevel with ``Loading_IMG.png``, dismisses after
~3 s or on first click/keypress, and deiconifies the root. Silent
no-op if the image asset is missing. Lives in its own module so
``main()`` in ``pm_gui`` reads as a plain orchestration layer.
"""

import os
import tkinter as tk


def show_splash(root: tk.Tk) -> None:
    """Show the splash image and reveal ``root`` afterwards."""
    img_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "Loading_IMG.png")
    try:
        photo = tk.PhotoImage(file=img_path)
    except tk.TclError:
        root.deiconify()
        return  # missing asset — skip splash silently

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    w, h = photo.width(), photo.height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    lbl = tk.Label(splash, image=photo, bd=0)
    lbl.pack()
    lbl.image = photo  # prevent GC

    def _dismiss():
        try:
            splash.destroy()
        except tk.TclError:
            pass
        root.deiconify()

    _id = root.after(3000, _dismiss)

    def _early(event=None):
        root.after_cancel(_id)
        _dismiss()

    splash.bind("<Button-1>", _early)
    splash.bind("<Key>", _early)
    lbl.bind("<Button-1>", _early)
    splash.focus_set()
