"""Profile selection popup — shown just-in-time when a commit needs a profile.

Backend priority: PyQt6 → tkinter (stdlib, always available).
The window is pre-loaded hidden on daemon start and shown quickly via show().
"""

from __future__ import annotations

import logging
from typing import List, Optional

from grit.models.profile import Profile

log = logging.getLogger(__name__)


def show_profile_picker(repo_name: str, profiles: List[Profile]) -> Optional[str]:
    """Show a profile selection dialog and return the chosen profile ID.

    Returns None if the user cancels (no profile selected).
    Attempts PyQt6 first; falls back to tkinter.
    """
    if not profiles:
        return None
    try:
        return _qt_picker(repo_name, profiles)
    except ImportError:
        pass
    try:
        return _tk_picker(repo_name, profiles)
    except Exception as exc:
        log.warning("Profile picker UI failed: %s", exc)
        return None


# ── PyQt6 backend ─────────────────────────────────────────────────────────────

def _qt_picker(repo_name: str, profiles: List[Profile]) -> Optional[str]:
    from PyQt6.QtWidgets import (  # type: ignore[import]
        QApplication, QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
        QDialogButtonBox,
    )
    from PyQt6.QtCore import Qt  # type: ignore[import]
    import sys

    app = QApplication.instance() or QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("Grit — Select Profile")
    layout = QVBoxLayout(dialog)

    layout.addWidget(QLabel(f"Choose a profile for <b>{repo_name}</b>:"))

    list_widget = QListWidget()
    for p in profiles:
        item = QListWidgetItem(f"{p.name}  <{p.email}>")
        item.setData(Qt.ItemDataRole.UserRole, p.id)
        list_widget.addItem(item)
    list_widget.setCurrentRow(0)
    layout.addWidget(list_widget)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    # Keyboard: Enter=OK, Escape=Cancel (handled by QDialog by default)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        item = list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
    return None


# ── tkinter backend ───────────────────────────────────────────────────────────

def _tk_picker(repo_name: str, profiles: List[Profile]) -> Optional[str]:
    import tkinter as tk
    from tkinter import ttk

    result: List[Optional[str]] = [None]

    root = tk.Tk()
    root.title("Grit — Select Profile")
    root.resizable(False, False)

    ttk.Label(root, text=f"Choose a profile for '{repo_name}':").pack(padx=12, pady=(12, 4))

    listbox = tk.Listbox(root, selectmode=tk.SINGLE, height=min(len(profiles), 8))
    for p in profiles:
        listbox.insert(tk.END, f"{p.name}  <{p.email}>")
    listbox.select_set(0)
    listbox.pack(padx=12, pady=4, fill=tk.BOTH, expand=True)

    def _ok() -> None:
        sel = listbox.curselection()
        if sel:
            result[0] = profiles[sel[0]].id
        root.destroy()

    def _cancel() -> None:
        root.destroy()

    frame = ttk.Frame(root)
    ttk.Button(frame, text="Select", command=_ok).pack(side=tk.RIGHT, padx=4)
    ttk.Button(frame, text="Cancel", command=_cancel).pack(side=tk.RIGHT, padx=4)
    frame.pack(padx=12, pady=(4, 12))

    root.bind("<Return>", lambda _: _ok())
    root.bind("<Escape>", lambda _: _cancel())
    root.lift()
    root.focus_force()
    root.mainloop()

    return result[0]
