"""Cross-topic search window for the ``?`` help content.

Opens from ``Help → Find in Help…`` in the main window. Lets users search
every help topic (main window, Line-up Coach, Byte Workbench, …) from a
single box; double-click a result to open that topic's ``HelpDialog``
with the query pre-highlighted.

Kept in its own module so no help-consuming Toplevel pulls in the search
UI it doesn't use.
"""

import tkinter as tk
from tkinter import ttk

from pm_core import help_text

from pm_gui_help import HelpDialog
from pm_gui_theme import PAL, _retro


class HelpSearchWindow(tk.Toplevel):
    """Search box + results list over every topic in ``help_text.HELP``."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Find in Help")
        self.geometry("720x440")
        self.minsize(520, 320)
        self.configure(bg=PAL["bg"])
        self.transient(parent)

        top = tk.Frame(self, bg=PAL["bg"])
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 6))

        tk.Label(
            top, text="Search:", bg=PAL["bg"], fg=PAL["fg_label"],
            font=_retro(11, "bold"),
        ).pack(side=tk.LEFT)

        self._query = tk.StringVar()
        self._query.trace_add("write", lambda *_: self._refresh())
        entry = tk.Entry(
            top, textvariable=self._query,
            bg=PAL["field"], fg=PAL["fg_data"],
            insertbackground=PAL["fg_data"],
            selectbackground=PAL["selected"],
            selectforeground=PAL["fg_white"],
            relief="flat", borderwidth=1,
            font=_retro(11),
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        entry.focus_set()

        self._status = tk.Label(
            self, text="Type to search across every help topic.",
            bg=PAL["bg"], fg=PAL["fg_dim"], anchor="w",
            font=_retro(10),
        )
        self._status.pack(side=tk.TOP, fill=tk.X, padx=10)

        list_frame = tk.Frame(self, bg=PAL["bg"])
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(4, 6))

        columns = ("topic", "context")
        self._tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse",
        )
        self._tree.heading("topic", text="Topic")
        self._tree.heading("context", text="Context")
        self._tree.column("topic", width=180, stretch=False)
        self._tree.column("context", width=500, stretch=True)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                               command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._tree.bind("<Double-1>", lambda e: self._open_selected())
        self._tree.bind("<Return>", lambda e: self._open_selected())
        entry.bind("<Return>", lambda e: self._open_first())
        entry.bind("<Down>", lambda e: self._focus_tree())

        btn_frame = tk.Frame(self, bg=PAL["bg"])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            btn_frame, text="Open", command=self._open_selected,
            bg=PAL["bg_mid"], fg=PAL["fg_data"],
            activebackground=PAL["selected"],
            activeforeground=PAL["fg_white"],
            relief="flat", borderwidth=1,
            font=_retro(10, "bold"),
        ).pack(side=tk.RIGHT, padx=(6, 0))

        tk.Button(
            btn_frame, text="Close", command=self.destroy,
            bg=PAL["bg_mid"], fg=PAL["fg_data"],
            activebackground=PAL["selected"],
            activeforeground=PAL["fg_white"],
            relief="flat", borderwidth=1,
            font=_retro(10, "bold"),
        ).pack(side=tk.RIGHT)

        self.bind("<Escape>", lambda e: self.destroy())

        # Seed with a gentle prompt: list every topic once so the window
        # is not blank on open.
        self._show_topic_index()

    def _show_topic_index(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for topic, entry in help_text.HELP.items():
            self._tree.insert(
                "", "end", iid=f"topic:{topic}",
                values=(entry["title"], "Open this topic — or start typing to search."),
            )
        self._status.configure(
            text=f"{len(help_text.HELP)} help topics available.",
        )

    def _refresh(self) -> None:
        query = self._query.get()
        if not query.strip():
            self._show_topic_index()
            return
        hits = help_text.search(query)
        self._tree.delete(*self._tree.get_children())
        for i, hit in enumerate(hits):
            self._tree.insert(
                "", "end", iid=f"hit:{i}",
                values=(hit.title, hit.line),
                tags=(hit.topic,),
            )
        if hits:
            self._status.configure(
                text=f"{len(hits)} match{'es' if len(hits) != 1 else ''} for "
                     f"\u201c{query}\u201d.",
            )
            first = self._tree.get_children()
            if first:
                self._tree.selection_set(first[0])
                self._tree.focus(first[0])
        else:
            self._status.configure(
                text=f"No matches for \u201c{query}\u201d.",
            )

    def _open_first(self) -> None:
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._open_selected()

    def _focus_tree(self) -> None:
        children = self._tree.get_children()
        if children:
            self._tree.focus_set()
            if not self._tree.selection():
                self._tree.selection_set(children[0])
                self._tree.focus(children[0])

    def _open_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        query = self._query.get().strip()
        if iid.startswith("topic:"):
            topic = iid.split(":", 1)[1]
        else:
            # hit:N — look up the topic via the row's tag
            tags = self._tree.item(iid, "tags")
            if not tags:
                return
            topic = tags[0]
        HelpDialog(self.master, topic, highlight=query or None)
