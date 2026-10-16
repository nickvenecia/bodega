"""Check Out / Check In: tick each piece as it leaves or comes back (or scan its label), note its condition and
add photos of it. Mark as Out (or Returned) when you're done; Save keeps your ticks for later."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from bodega.core import dates, document, errors
from bodega.core.checks import pieces, progress, rows
from bodega.core.model import CheckRow, Rental, now_iso
from bodega.ui.components import photos
from bodega.ui.components.widgets import (
    ElidedLabel,
    FitScroll,
    Guarded,
    button_row,
    hbox,
    hint,
    icon_button,
    status_line,
    vbox,
)
from bodega.ui.style import tokens


class _Row(QFrame):
    def __init__(self, c: CheckRow, name: str, units: int, serials: str, back: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("CheckRow")
        self.c = c
        self.back = back
        lay = vbox(self, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_3, tokens.SPACE_2), tokens.SPACE_1)
        top = hbox(spacing=tokens.SPACE_2)
        self.tick = QCheckBox()
        self.tick.setChecked(c.back if back else c.out)
        self.tick.toggled.connect(self._ticked)
        top.addWidget(self.tick)
        label = ElidedLabel(f"{name}  ×{units}" if units > 1 else name)
        top.addWidget(label, 1)
        self.shots = QWidget()
        self.shots_lay = hbox(self.shots, 0, tokens.SPACE_1)
        top.addWidget(self.shots)
        cam = icon_button("camera", "Add a photo of its condition")
        cam.clicked.connect(self._add_photo)
        top.addWidget(cam)
        lay.addLayout(top)
        if serials:
            s = hint(serials)
            lay.addWidget(s)
        self.note = QLineEdit(c.note)
        self.note.setPlaceholderText("Condition, damage…")
        self.note.textEdited.connect(lambda t: setattr(self.c, "note", t))
        lay.addWidget(self.note)
        self._show_photos()

    def _ticked(self, on: bool) -> None:
        """Ticked, with the time it was (what left when, and came back when, if a piece goes missing)."""
        when = now_iso() if on else ""
        if self.back:
            self.c.back, self.c.back_at = on, when
        else:
            self.c.out, self.c.out_at = on, when
        self.setToolTip(f"Ticked {dates.fmt_moment(when)}" if when else "")

    def _show_photos(self) -> None:
        while self.shots_lay.count():
            w = self.shots_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for name in self.c.photos[-4:]:
            pix = photos.thumbnail(name, tokens.TABLE_THUMB, self.devicePixelRatioF())
            if pix is not None:
                lbl = QLabel()
                lbl.setPixmap(pix)
                self.shots_lay.addWidget(lbl)

    def _add_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Add a Photo", "", "Pictures (*.jpg *.jpeg *.png *.webp *.heic *.gif)"
        )
        if not path:
            return
        try:
            self.c.photos.append(photos.keep_file(Path(path)))
        except ValueError as e:
            self.window().say(str(e))
            return
        except OSError as e:
            self.window().say(errors.plain(e, "add that photo"))
            return
        self._show_photos()


class CheckDialog(Guarded, QDialog):
    """`back`: checking in (otherwise out). After it closes, `.rows` and `.mark` (True: Mark as Out / Returned)."""

    def __init__(self, lib, r: Rental, back: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.back = back
        self.mark = False
        title = f"Check In {r.number}" if back else f"Check Out {r.number}"
        self.setWindowTitle(title)
        self.setMinimumSize(tokens.DIALOG_W_WIDE, tokens.PAGE_DIALOG_MIN_H)
        self.rows = [replace(c, photos=list(c.photos)) for c in rows(lib, r)]  # edited here; kept on Save
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        t = QLabel(title)
        t.setObjectName("DialogTitle")
        lay.addWidget(t)
        self.scan = QLineEdit()
        self.scan.setPlaceholderText("Scan a label, or tick each piece")
        self.scan.returnPressed.connect(self._scanned)
        lay.addWidget(self.scan)
        self.status = status_line()
        lay.addWidget(self.status)
        body = QWidget()
        bl = vbox(body, (0, 0, tokens.SPACE_3, 0), tokens.SPACE_2)
        units = {it.id: (it, n) for it, n in pieces(lib, r)}
        self.widgets: dict[str, _Row] = {}
        for c in self.rows:
            it, n = units.get(c.item_id, (lib.items.get(c.item_id), 1))
            name = it.name if it is not None else "Removed gear"
            serials = ", ".join(it.serial_list()) if it is not None else ""
            w = _Row(c, name, n, f"S/N {serials}" if serials else "", back)
            w.tick.toggled.connect(lambda _on: self._count())
            bl.addWidget(w)
            self.widgets[c.item_id] = w
        bl.addStretch(1)
        self.scroll = FitScroll()
        self.scroll.setWidget(body)
        lay.addWidget(self.scroll, 1)
        row = button_row()
        self.progress = status_line()
        row.insertWidget(0, self.progress)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setToolTip("Keep the ticks and notes, and finish later")
        save.clicked.connect(self.accept)
        self.go = QPushButton("Mark as Returned" if back else "Mark as Out")
        self.go.setObjectName("Primary")
        self.go.setDefault(True)
        self.go.clicked.connect(self._mark)
        for b in (cancel, save, self.go):
            row.addWidget(b)
        lay.addLayout(row)
        self._count()
        self.scan.setFocus()
        self.settled()

    def form_values(self) -> object:
        return [(c.out, c.back, c.note, tuple(c.photos)) for c in self.rows]

    def say(self, text: str) -> None:
        self.status.setText(text)

    def _count(self) -> None:
        done, total = progress(self.rows, self.back)
        self.progress.setText(f"{done} of {total} {'back' if self.back else 'ticked'}")

    def _scanned(self) -> None:
        item_id = document.item_from_code(self.scan.text())
        self.scan.clear()
        w = self.widgets.get(item_id or "")
        if w is None:
            self.say("That label isn't on this rental." if item_id else "That isn't a Bodega label.")
            return
        w.tick.setChecked(True)
        self.scroll.ensureWidgetVisible(w)
        self.say("")

    def _mark(self) -> None:
        from bodega.ui.dialogs.common import confirm

        done, total = progress(self.rows, self.back)
        if done < total:
            left = total - done
            what = "returned" if self.back else "out"
            if not confirm(
                self,
                f"{left} piece{'s' if left != 1 else ''} not ticked",
                f"Mark the rental as {what} anyway?",
                "Mark as Returned" if self.back else "Mark as Out",
                danger=False,
            ):
                return
        self.mark = True
        self.accept()

    def keyPressEvent(self, e):
        # Return in the scan box scans, in a note it's done: neither presses Mark as Out
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and isinstance(self.focusWidget(), QLineEdit):
            return
        super().keyPressEvent(e)
