"""Small dialogs: alerts (confirm, notice), names, Tidy Up's preview, and the About box."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from bodega.core import words
from bodega.ui.components.widgets import button_row, combo, hbox, hint, suggestions, vbox
from bodega.ui.style import tokens
from bodega.ui.style.tokens import DIALOG_W, SPACE_3, SPACE_5
from bodega.ui.style.tokens import IMPORT_LIST_H as PICKER_LIST_H


class Alert(QDialog):
    """A Mac-style alert: the app's icon, a bold question, a line of detail, its buttons. Esc cancels. Return
    does the action, unless `safe` (the loss is a side effect nobody asked for): then Return does the cancel
    button. A third button (`other`) stacks the three, the action on top; exec() returns OTHER for it.
    A rounded card floating over the window, with no title bar."""

    OTHER = 2

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        text: str,
        action: str,
        cancel: str = "",
        danger=False,
        other: str = "",
        safe: bool = False,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(title)
        outer = vbox(self, 0, 0)
        card = QFrame()
        card.setObjectName("Alert")
        card.setFixedWidth(tokens.ALERT_W)
        outer.addWidget(card)
        lay = vbox(card, (tokens.SPACE_5, tokens.SPACE_5, tokens.SPACE_5, tokens.SPACE_4), tokens.SPACE_2)
        icon = QLabel()
        app_icon = QApplication.windowIcon()
        if not app_icon.isNull():
            icon.setPixmap(app_icon.pixmap(tokens.ALERT_ICON, tokens.ALERT_ICON))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(icon)
            lay.addSpacing(tokens.SPACE_1)
        t = QLabel(title)
        t.setObjectName("AlertTitle")
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        if text:
            body = hint(text)
            body.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(body)
        lay.addSpacing(tokens.SPACE_3)
        go = QPushButton(action)
        go.setObjectName("DangerFill" if danger else "Primary")
        go.clicked.connect(self.accept)
        no = None
        if cancel:
            no = QPushButton(cancel)
            no.clicked.connect(self.reject)
        third = None
        if other:
            third = QPushButton(other)
            third.setObjectName("DangerFill")
            third.clicked.connect(lambda: self.done(self.OTHER))
        if third is not None:  # three stack: the action on top, Cancel at the bottom
            for b in (go, third, no):
                if b is not None:
                    lay.addWidget(b)
        else:  # two side by side: Cancel leading, the action trailing
            row = hbox(spacing=tokens.SPACE_2)
            if no is not None:
                row.addWidget(no, 1)
            row.addWidget(go, 1)
            lay.addLayout(row)
        self.go = no if safe and no is not None else go  # what Return does
        for b in (go, no, third):
            if b is not None:
                b.setAutoDefault(b is self.go)
                b.setDefault(b is self.go)

    def showEvent(self, e):
        super().showEvent(e)
        self.go.setFocus()
        win = self.parentWidget().window() if self.parentWidget() is not None else None
        if win is not None:  # over the middle of the window, a little above centre, like a Mac alert
            g = win.frameGeometry()
            self.move(g.center().x() - self.width() // 2, g.top() + g.height() // 3 - self.height() // 2)


def confirm(parent: QWidget, title: str, text: str, action: str, danger: bool = True) -> bool:
    """Ask before doing something big. Return says yes (you pressed Delete to get here); Esc says no."""
    return Alert(parent, title, text, action, "Cancel", danger).exec() == QDialog.DialogCode.Accepted


def ask_discard(parent: QWidget) -> bool:
    """Typing would be lost (Cancel, Esc, closing, going elsewhere): True to Discard Changes. Return and Esc
    Keep Editing."""
    return (
        Alert(
            parent,
            "Discard Your Changes?",
            "What you changed here hasn't been saved.",
            "Discard Changes",
            "Keep Editing",
            danger=True,
            safe=True,
        ).exec()
        == QDialog.DialogCode.Accepted
    )


def notice(parent: QWidget, title: str, text: str) -> None:
    """Something went wrong and it needs more than a toast to say why."""
    Alert(parent, title, text, "OK").exec()


def ask_name(
    parent: QWidget,
    title: str,
    action: str,
    text: str = "",
    placeholder: str = "",
    known: list[str] | None = None,
) -> str | None:
    """One name, typed (a new department, a renamed group). None if cancelled or left blank."""
    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    t = QLabel(title)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    field = QLineEdit(text)
    field.setPlaceholderText(placeholder)
    field.selectAll()
    if known:
        c = QCompleter(known, field)
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        field.setCompleter(suggestions(c))
    lay.addWidget(field)
    row = button_row()
    cancel = QPushButton("Cancel")
    cancel.clicked.connect(d.reject)
    go = QPushButton(action)
    go.setObjectName("Primary")
    go.setDefault(True)
    go.clicked.connect(d.accept)
    go.setEnabled(bool(text.strip()))
    field.textChanged.connect(lambda t: go.setEnabled(bool(t.strip())))
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    if d.exec() != QDialog.DialogCode.Accepted:
        return None
    return field.text().strip() or None


def ask_choice(
    parent: QWidget, title: str, text: str, choices: list[tuple[str, str]], action: str
) -> str | None:
    """One of a few choices ((key, words) each), picked from a dropdown. The key, or None if cancelled."""
    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    t = QLabel(title)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    if text:
        lay.addWidget(hint(text))
    pick = combo([(key, label, "") for key, label in choices], choices[0][0] if choices else "")
    lay.addWidget(pick)
    row = button_row()
    cancel = QPushButton("Cancel")
    cancel.clicked.connect(d.reject)
    go = QPushButton(action)
    go.setObjectName("Primary")
    go.setDefault(True)
    go.clicked.connect(d.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    if d.exec() != QDialog.DialogCode.Accepted:
        return None
    return pick.currentData()


def pick_from(parent: QWidget, title: str, choices: list[tuple[str, str]], action: str) -> str | None:
    """One of many choices ((key, words) each) from a list you can search: type to narrow it, ↓ into the list,
    Return or a double-click picks. The key, or None if cancelled."""
    from PySide6.QtWidgets import QListWidget, QListWidgetItem

    from bodega.core import search
    from bodega.ui.components.widgets import SearchField

    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    t = QLabel(title)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    find = SearchField()
    find.setPlaceholderText("Search")
    find.setAccessibleName("Search")
    lay.addWidget(find)
    box = QListWidget()
    box.setObjectName("Picker")
    box.setFixedHeight(PICKER_LIST_H)
    for key, label in choices:
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        box.addItem(item)
    box.setCurrentRow(0)
    lay.addWidget(box)

    def narrow(text: str) -> None:
        wanted = search.words(text)
        first = None
        for i in range(box.count()):
            item = box.item(i)
            hide = not search.matches(search.folded(item.text()), wanted)
            item.setHidden(hide)
            if not hide and first is None:
                first = item
        if first is not None:
            box.setCurrentItem(first)

    find.textChanged.connect(narrow)
    find.down_wanted.connect(box.setFocus)
    find.returnPressed.connect(
        lambda: box.currentItem() is not None and not box.currentItem().isHidden() and d.accept()
    )
    box.itemDoubleClicked.connect(lambda _i: d.accept())
    row = button_row()
    cancel = QPushButton("Cancel")
    cancel.clicked.connect(d.reject)
    go = QPushButton(action)
    go.setObjectName("Primary")
    go.setDefault(True)
    go.clicked.connect(d.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    find.setFocus()
    if d.exec() != QDialog.DialogCode.Accepted or box.currentItem() is None or box.currentItem().isHidden():
        return None
    return box.currentItem().data(Qt.ItemDataRole.UserRole)


def tidy_preview(parent: QWidget, moves: list) -> bool:
    """Show what Tidy Up Groups would do (old group → new group, how many) and ask before doing it."""
    from collections import Counter

    from PySide6.QtWidgets import QListWidget

    d = QDialog(parent)
    d.setWindowTitle("Tidy Up Groups")
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    t = QLabel("Tidy Up Groups")
    t.setObjectName("DialogTitle")
    lay.addWidget(t)
    lay.addWidget(
        hint(f"{words.count(len(moves), 'piece')} {'gets' if len(moves) == 1 else 'get'} a clearer group.")
    )
    box = QListWidget()
    box.setObjectName("Picker")
    pairs = Counter((old or "No Group", new or "No Group") for _it, old, new in moves)
    for (old, new), n in sorted(pairs.items(), key=lambda x: (x[0][1], x[0][0])):
        box.addItem(f"{old}  →  {new}   ·  {n}")
    box.setMinimumHeight(PICKER_LIST_H)
    lay.addWidget(box)
    row = button_row()
    cancel = QPushButton("Cancel")
    cancel.clicked.connect(d.reject)
    go = QPushButton("Tidy Up")
    go.setObjectName("Primary")
    go.setDefault(True)
    go.clicked.connect(d.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    return d.exec() == QDialog.DialogCode.Accepted


def about(parent: QWidget, version: str, data_folder: str) -> None:
    d = QDialog(parent)
    d.setWindowTitle("About Bodega")
    d.setMinimumWidth(DIALOG_W)
    lay = vbox(d, SPACE_5, SPACE_3)
    from bodega.ui.style import theme

    word = QLabel(theme.wordmark())
    word.setObjectName("Wordmark")
    word.setTextFormat(Qt.TextFormat.RichText)
    lay.addWidget(word)
    lay.addWidget(hint(f"Version {version}. Keep track of your gear, put it in kits, rent it out."))
    lay.addWidget(hint(f"Your gear and rentals are saved on this computer only, in {data_folder}"))
    lay.addWidget(hint("Open source under GPL-3.0. Fonts under the SIL Open Font License."))
    row = button_row()
    ok = QPushButton("Done")
    ok.setObjectName("Primary")
    ok.clicked.connect(d.accept)
    row.addWidget(ok)
    lay.addLayout(row)
    d.exec()
