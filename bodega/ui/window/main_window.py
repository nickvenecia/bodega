"""The window, full screen: the sidebar | a big table of gear, kits or rentals | the selected one, editable.

Pick a place in the sidebar (all gear, a group, kits, rentals), click a row, change it on the right.
Agreements, kit sheets, the inventory list and the rate card open in their own window when you ask for them.
Edits save themselves a moment after you stop typing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QByteArray, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from bodega.core import backups, dates, document, money, pricing, settings, update
from bodega.core.history import History
from bodega.core.log import get_logger
from bodega.core.model import Business
from bodega.core.store import Library
from bodega.ui.components import titlebar
from bodega.ui.components.empty import EmptyPage, NoResults
from bodega.ui.components.glass import Dock, GlassRoot, glass
from bodega.ui.components.widgets import Banner, ElidedLabel, SearchField, Toast, hbox, vbox
from bodega.ui.dialogs.preview import PageDialog
from bodega.ui.panels.item import ItemPanel
from bodega.ui.panels.kit import PackagePanel
from bodega.ui.panels.rental import RentalPanel
from bodega.ui.style import theme, tokens
from bodega.ui.window.ai import AIMixin
from bodega.ui.window.calendar_view import CalendarPage
from bodega.ui.window.common import TITLES, kind_of
from bodega.ui.window.editing import EditingMixin
from bodega.ui.window.filters import FilterButton, FilterChips
from bodega.ui.window.groups import GroupsMixin
from bodega.ui.window.menus import MenusMixin
from bodega.ui.window.pages import PagesMixin
from bodega.ui.window.services import ServicesMixin
from bodega.ui.window.sidebar import Sidebar
from bodega.ui.window.tables import DIVIDES, ID, GearTable, KitTable, RentalTable, menu, words_inset
from bodega.ui.window.transfer import TransferMixin

log = get_logger(__name__)


class MainWindow(AIMixin, MenusMixin, GroupsMixin, EditingMixin, TransferMixin, PagesMixin, ServicesMixin, QMainWindow):
    def __init__(self, lib: Library | None = None):
        super().__init__()
        self.lib = lib or Library().load()
        self.setWindowTitle("Bodega")
        self.resize(*tokens.WINDOW_SIZE)
        self.setMinimumSize(*tokens.WINDOW_MIN)
        self._dirty_items = False
        self._dirty_packages = False
        self._dirty_rentals: set[str] = set()
        self.history: History | None = None
        self._fresh: tuple[str, str, dict] | None = None  # a new piece/kit/rental not filled in yet
        self.last_export: Path | None = None
        self._release: update.Release | None = None
        self.view_key = "gear"
        self.page_ctx: tuple[str, str] = ("gear", "")
        self.page: PageDialog | None = None

        root = GlassRoot()
        self.root = root
        outer = vbox(root, 0, 0)
        self.titlebar = titlebar.install(self)
        if self.titlebar is not None:
            outer.addWidget(self.titlebar)
        gap = tokens.GLASS_GAP
        body = hbox(spacing=gap)
        body.setContentsMargins(gap, 0 if self.titlebar is not None else gap, gap, gap)
        self.sidebar = glass(Sidebar(self.lib))
        root.float(self.sidebar)
        body.addWidget(self.sidebar)
        body.addWidget(self._build_center(), 1)
        self.items = ItemPanel(self.lib)
        self.packages = PackagePanel(self.lib)
        self.rentals = RentalPanel(self.lib)
        self.rentals.may_hold = self.may_hold
        self.assistant = self._build_assistant()
        self.inspector = glass(QStackedWidget())  # the glass panel on the right…
        for w in (self.items, self.packages, self.rentals, self.assistant):
            self.inspector.addWidget(w)
        self.dock = Dock(self.inspector, root, self.sidebar, body)  # …which slides in when something's picked
        self.dock.toggled.connect(lambda _on: self._mark_assistant())
        self.inspector.currentChanged.connect(lambda _i: self._mark_assistant())
        self.dock.follower = lambda: self.pages.currentWidget()
        outer.addLayout(body, 1)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.escape)
        self.setCentralWidget(root)
        self.toaster = Toast(self, self._toast_area)

        self._save_timer = QTimer(self, singleShot=True, interval=tokens.SAVE_DELAY_MS, timeout=self.flush)
        self._save_cap = QTimer(self, singleShot=True, interval=tokens.SAVE_MAX_MS, timeout=self.flush)
        self._retry_timer = QTimer(self, interval=tokens.SAVE_RETRY_MS, timeout=self.flush)  # while not saved
        self._was_unsaved = False
        self.lib.on_unsaved = lambda: QTimer.singleShot(0, self, self.show_save_state)
        self._table_timer = QTimer(self, singleShot=True, interval=tokens.TABLE_DELAY_MS, timeout=self.refresh)

        self._wire()
        self._menus()
        self.look_changed()
        groups = self.lib.settings.get("groups", {})
        groups = groups if isinstance(groups, dict) else {}
        for panel in (self.items, self.packages, self.rentals):
            g = groups.get(panel.KEY)
            if isinstance(g, dict):
                panel.set_open_groups(g)
        hidden = self.lib.settings.get("hidden_columns")
        if isinstance(hidden, list):
            self.gear_table.hidden_cols = {x for x in hidden if isinstance(x, str)}
            known = self.lib.settings.get("columns_known")
            known = set(known) if isinstance(known, list) else set()
            self.gear_table.hidden_cols |= {"earned"} - known  # columns added since start tucked away
        self.lib.settings["columns_known"] = ["earned"]
        if not settings.value(self.lib.settings, "companies_guessed"):  # gear from before Company existed
            if self.lib.guess_brands():
                self.lib.save_items()
            self.lib.settings["companies_guessed"] = True
        folded = settings.value(self.lib.settings, "folded")
        self.gear_table.folded = {x for x in folded if isinstance(x, str)} if isinstance(folded, list) else set()
        self._restored = False  # True: open at the size already set (screenshots), not the saved one
        view = settings.value(self.lib.settings, "view")
        self.go(view if isinstance(view, str) else "gear")
        self.history = History(self.lib)  # undo/redo starts from how things are when the window opens
        backups.daily_copy(self.lib.root)  # the first time Bodega opens today: a safety copy
        if self.lib.newer_format:
            QTimer.singleShot(0, self, self._say_newer_format)
        QTimer.singleShot(tokens.UPDATE_CHECK_DELAY_MS, self._auto_check_updates)
        self._day = dates.today()  # a new day refreshes what "today" decides: late, out now, coming up
        self._midnight = QTimer(self, singleShot=True, timeout=self._new_day)
        self._arm_midnight()
        QGuiApplication.instance().applicationStateChanged.connect(self._app_state)

    # The day, and going to the background
    def _arm_midnight(self) -> None:
        now = datetime.now()
        nxt = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        self._midnight.start(int((nxt - now).total_seconds() * 1000) + tokens.MIDNIGHT_SLACK_MS)

    def _new_day(self) -> None:
        """Past midnight (or back to Bodega on another day): late rentals, Out Now and Coming Up go by today."""
        if dates.today() != self._day:
            self._day = dates.today()
            backups.daily_copy(self.lib.root)  # today's safety copy
            self.refresh()
        self._arm_midnight()

    def _app_state(self, state) -> None:
        if state == Qt.ApplicationState.ApplicationActive:
            self._new_day()  # a computer asleep over midnight misses the timer
        elif state in (Qt.ApplicationState.ApplicationInactive, Qt.ApplicationState.ApplicationHidden):
            self.flush()  # going to another app: what you typed is saved now

    # Building
    def _build_center(self) -> QWidget:
        center = QFrame()
        center.setObjectName("Center")
        lay = vbox(center, 0, 0)
        bar = QFrame()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(tokens.TOOLBAR_H)
        # three parts: the title on the left, the search and filters centred, the buttons on the right
        grid = QGridLayout(bar)
        grid.setContentsMargins(tokens.PAGE_INSET, 0, tokens.PAGE_INSET, 0)  # the page's two edges
        grid.setHorizontalSpacing(tokens.SPACE_4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        left = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel("All Gear")
        self.title.setObjectName("PageTitle")
        self.count = ElidedLabel()  # "131", or "5 selected": gives way before the search and dropdowns do
        self.count.setObjectName("PageCount")
        self.count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        left.addWidget(self.title)
        left.addWidget(self.count)
        left.addStretch(1)
        grid.addLayout(left, 0, 0)
        mid = hbox(spacing=tokens.SPACE_2)
        self.search = SearchField()
        self.search.setPlaceholderText("Search")
        self.search.setProperty("capsule", True)
        self.search.setProperty("bar", True)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(tokens.SEARCH_MIN)  # shrinks before anything squeezes together
        self.search.setMaximumWidth(tokens.SEARCH_W)
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(lambda _t: self._apply_search())
        self.search.returnPressed.connect(self._scanned)  # a label's QR code, read by a scanner (else: open)
        self.search.down_wanted.connect(self._into_list)
        mid.addWidget(self.search)
        # how the list is divided and what it shows, behind one icon (the accent while a filter hides gear)
        self.view_menu = FilterButton(self.lib.brands)
        self.view_menu.changed.connect(self._view_picked)
        mid.addWidget(self.view_menu)
        grid.addLayout(mid, 0, 1, Qt.AlignmentFlag.AlignCenter)
        right = hbox(spacing=tokens.SPACE_2)
        right.addStretch(1)
        self.btn_export = QToolButton()
        self.btn_export.setObjectName("Circle")
        self.btn_export.setIcon(theme.icon("share", theme.MUTED, tokens.ICON_BAR))
        self.btn_export.setIconSize(QSize(tokens.ICON_BAR, tokens.ICON_BAR))
        self.btn_export.setToolTip("Print or Share: inventory list, rate card, labels")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setProperty("bar", True)
        right.addWidget(self.btn_export)
        self.btn_ai = QToolButton()
        self.btn_ai.setObjectName("Circle")
        self.btn_ai.setIcon(theme.icon("assistant", theme.ACCENT, tokens.ICON_LG))
        self.btn_ai.setIconSize(QSize(tokens.ICON_LG, tokens.ICON_LG))
        self.btn_ai.setToolTip("AI Assistant (⌘J)")
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.setProperty("bar", True)
        self.btn_ai.setCheckable(True)  # on while the assistant is open
        self.btn_ai.clicked.connect(self.toggle_assistant)
        self.btn_new = QToolButton()
        self.btn_new.setObjectName("CirclePrimary")
        self.btn_new.setIcon(theme.icon("plus", theme.ON_ACCENT, tokens.ICON_BAR))
        self.btn_new.setIconSize(QSize(tokens.ICON_BAR, tokens.ICON_BAR))
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setProperty("bar", True)
        self.btn_new.clicked.connect(lambda: self.new(kind_of(self.view_key)))
        right.addWidget(self.btn_new)
        right.addWidget(self.btn_ai)  # the assistant comes last, after the page's one main action
        grid.addLayout(right, 0, 2)
        lay.addWidget(bar)
        self.toolbar = bar
        self.filter_chips = FilterChips()  # what the filter's hiding, each with its ✕
        self.filter_chips.removed.connect(self._filter_off)
        lay.addWidget(self.filter_chips)
        self.banner = Banner("Try Again")  # a save that failed, until it works
        self.banner.acted.connect(self.try_saving_again)
        lay.addWidget(self.banner)

        self.pages = QStackedWidget()
        self.gear_table = GearTable()
        self.kit_table = KitTable()
        self.rental_table = RentalTable()
        self.calendar = CalendarPage()  # Month or Timeline
        self.calendar.set_mode(settings.value(self.lib.settings, "calendar_mode"), quiet=True)
        self.calendar.mode_changed.connect(lambda m: self.lib.settings.__setitem__("calendar_mode", m))
        cal_scroll = self.calendar
        self.cal_scroll = cal_scroll
        self.empty = EmptyPage()  # where the table would be, with nothing in it yet
        self.empty.dropped.connect(self.import_file)
        self.no_results = NoResults()  # over a table when a search or the filters hide every row
        self.no_results.clear_wanted.connect(self._clear_hiding)
        for w in (self.gear_table, self.kit_table, self.rental_table, cal_scroll, self.empty):
            self.pages.addWidget(w)
        # one left edge and one right edge: a list's words line up with the title and the bar's last button
        edge = max(0, tokens.PAGE_INSET - words_inset(self.gear_table))
        box = QWidget()
        vbox(box, (edge, 0, edge, 0), 0).addWidget(self.pages)
        self.calendar.set_edge(tokens.PAGE_INSET - edge)  # (the calendar's own words have no cell around them)
        lay.addWidget(box, 1)
        self.totals = QFrame()
        self.totals.setObjectName("Totals")
        tl = hbox(self.totals, (tokens.PAGE_INSET, tokens.SPACE_3, tokens.PAGE_INSET, tokens.SPACE_3), tokens.SPACE_5)
        self.total_values: dict[str, QLabel] = {}
        self.total_labels: dict[str, QLabel] = {}
        tl.addStretch(1)
        for key, label in (
            ("pieces", "Pieces"),
            ("paid", "Paid"),
            ("tax", "Tax"),
            ("value", "With Tax"),
            ("day", "Day Rate, Everything"),
        ):
            box = vbox(spacing=0)
            k = QLabel(label)
            k.setObjectName("TotalLabel")
            v = QLabel()
            v.setObjectName("TotalValue")
            theme.use_tabular(v)
            k.setAlignment(Qt.AlignmentFlag.AlignRight)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            box.addWidget(k)
            box.addWidget(v)
            tl.addLayout(box)
            self.total_values[key] = v
            self.total_labels[key] = k
        lay.addWidget(self.totals)
        return center

    def _wire(self) -> None:
        sb = self.sidebar
        sb.picked.connect(self._place_picked)
        sb.profile_card.clicked.connect(self._app_menu)
        sb.btn_update.clicked.connect(self.show_update)
        self.gear_table.picked.connect(lambda i: self.open("gear", i))
        self.kit_table.picked.connect(lambda i: self.open("packages", i))
        self.rental_table.picked.connect(lambda i: self.open("rentals", i))
        self.calendar.picked.connect(lambda i: self.open("rentals", i))
        self.gear_table.menu_wanted.connect(lambda i, pos: self._row_menu("gear", i, pos))
        self.kit_table.menu_wanted.connect(lambda i, pos: self._row_menu("packages", i, pos))
        self.rental_table.menu_wanted.connect(lambda i, pos: self._row_menu("rentals", i, pos))
        self.gear_table.folds_changed.connect(self._remember_folds)
        self.gear_table.divider_menu.connect(self._divider_menu)
        self.gear_table.dropped.connect(self.move_gear)
        self.gear_table.delete_wanted.connect(self.delete_gear)
        for t in (self.gear_table, self.kit_table, self.rental_table):
            t.cleared.connect(self.deselect)
        self.gear_table.reordered.connect(self._reordered)
        self.gear_table.branded.connect(self._branded)
        self.gear_table.columns_changed.connect(self._columns_changed)
        self.gear_table.itemSelectionChanged.connect(self._selection_count)
        self.kit_table.delete_wanted.connect(lambda ids: self.delete("packages", ids[0]))
        self.rental_table.delete_wanted.connect(lambda ids: self.delete("rentals", ids[0]))
        sb.menu_wanted.connect(self._sidebar_menu)
        sb.dropped.connect(self._sidebar_dropped)
        sb.new_group.connect(self.new_group)
        sb.new_rental.connect(lambda: self.new("rentals"))
        it = self.items
        it.changed.connect(self._item_edited)
        it.toast_wanted.connect(self.toast)
        it.ai_wanted.connect(self.ai_this_piece)
        it.structure_changed.connect(self._structure_changed)
        it.open_item.connect(lambda i: self.open("gear", i))
        it.attach_wanted.connect(self.attach_to)
        it.detach_wanted.connect(self.detach)
        it.duplicate_wanted.connect(lambda i: self.duplicate("gear", i))
        self.packages.duplicate_wanted.connect(lambda i: self.duplicate("packages", i))
        self.rentals.duplicate_wanted.connect(lambda i: self.duplicate("rentals", i))
        for panel in (self.items, self.packages, self.rentals):
            panel.close_wanted.connect(self.deselect)  # the round ✕
        it.delete_wanted.connect(lambda i: self.delete("gear", i))
        it.rent_wanted.connect(lambda _i: self.rent_this())
        it.open_rental.connect(lambda i: self.open("rentals", i))
        p = self.packages
        p.changed.connect(self._package_edited)
        p.add_wanted.connect(self.add_to_package)
        p.open_item.connect(lambda i: self.open("gear", i))
        p.delete_wanted.connect(lambda i: self.delete("packages", i))
        p.sheet_wanted.connect(lambda i: self.show_pages(("kit", i)))
        r = self.rentals
        r.changed.connect(self._rental_edited)
        r.status_changed.connect(lambda _r: (self.flush(), self.refresh()))
        r.business_wanted.connect(lambda kind: self.edit_business(kind == "add"))
        r.client_wanted.connect(lambda kind: self.edit_client(kind == "new"))
        r.add_wanted.connect(self.add_to_rental)
        r.open_item.connect(lambda i: self.open("gear", i))
        r.defaults_saved.connect(self._defaults_saved)
        r.delete_wanted.connect(lambda i: self.delete("rentals", i))
        r.calendar_wanted.connect(self.add_to_calendar)
        r.check_wanted.connect(self.check_rental)
        r.saldo_wanted.connect(self.send_to_saldo)
        r.sheet_wanted.connect(lambda i: self.show_pages(("rental", i)))
        for panel in (self.items, self.packages, self.rentals):
            panel.groups_changed.connect(self._groups_changed)

    # Where you are
    def business(self) -> Business | None:
        cur = settings.value(self.lib.settings, "business")
        return self.lib.businesses.get(cur) or next(iter(self.lib.businesses.values()), None)

    def _grp(self) -> str:
        return self.view_key[4:] if self.view_key.startswith("grp:") else ""

    def _divide_for(self, view: str) -> str:
        """How the gear table is divided: by group in All Gear, by company inside a group (each remembered)."""
        saved = self.lib.settings.get("divide")
        saved = saved if isinstance(saved, dict) else {}
        place = "grp" if view.startswith("grp:") else "all"
        default = "brand" if place == "grp" else "group"
        got = saved.get(place, default)
        return got if got in {k for k, _l, _t in DIVIDES} else default

    def _view_picked(self) -> None:
        saved = self.lib.settings.get("divide")
        saved = saved if isinstance(saved, dict) else {}
        saved["grp" if self.view_key.startswith("grp:") else "all"] = self.view_menu.divide
        self.lib.settings["divide"] = saved
        self.refresh()

    def set_gear_filter(self, key: str) -> None:
        self.view_menu.filter.show = key
        self.view_menu.show_state()
        self.refresh()

    def go(self, view: str) -> None:
        """Show a place from the sidebar."""
        self.flush()
        self._drop_fresh()
        if view.startswith("grp:") and view[4:] not in self.lib.groups():
            view = "gear"
        if view not in TITLES and not view.startswith("grp:"):
            view = "gear"
        moved = view != self.view_key  # another place: it starts unsearched and unfiltered
        self.view_key = view
        self.lib.settings["view"] = view
        self.sidebar.select(view)
        self.title.setText(self._grp() or TITLES.get(view, ""))
        kind = kind_of(view)
        self.btn_export.setVisible(kind == "gear" and bool(self.lib.items))  # nothing to print yet: no share
        self.btn_new.setToolTip({"gear": "New Gear or Group", "packages": "New Kit", "rentals": "New Rental"}[kind])
        gear_page = kind == "gear"  # on gear pages the + asks: a piece, or a group
        self.btn_new.setMenu(self.new_menu if gear_page else None)
        self.btn_new.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup if gear_page else QToolButton.ToolButtonPopupMode.DelayedPopup
        )
        self.view_menu.set_divide(self._divide_for(view), "brand" if view.startswith("grp:") else "group")
        if moved:
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            self.view_menu.clear_filter()
        if self.assistant_showing():  # the assistant stays while you move around
            self.refresh()
            self._ai_state()
            return
        self.inspector.setCurrentWidget({"gear": self.items, "packages": self.packages, "rentals": self.rentals}[kind])
        self.refresh()
        # keep what's open if it's still here; otherwise nothing is picked and the panel slides away
        cur = {"gear": self.items.it, "packages": self.packages.pkg, "rentals": self.rentals.r}[kind]
        table = self._table()
        if cur is not None and table is not None and self._in_table(cur.id) and self.dock.opened:
            table.select_id(cur.id)
            self._load(kind, cur.id)
        else:
            self._inspector_empty(kind)

    def _table(self):
        return {
            "gear": self.gear_table,
            "packages": self.kit_table,
            "rentals": None if self.view_key == "calendar" else self.rental_table,
        }[kind_of(self.view_key)]

    def _in_table(self, obj_id: str) -> bool:
        t = self._table()
        if t is None:
            return False
        stack = [t.topLevelItem(i) for i in range(t.topLevelItemCount())]
        while stack:
            r = stack.pop()
            if r.data(0, ID) == obj_id and not r.isHidden():
                return True
            stack.extend(r.child(i) for i in range(r.childCount()))
        return False

    def refresh(self) -> None:
        """Fill the table for where you are (and the sidebar's counts): one pass over everything."""
        with pricing.indexed(self.lib):
            self._refresh()

    def _refresh(self) -> None:
        lib, b = self.lib, self.lib.pricing()
        if self.view_key.startswith("grp:") and self._grp() not in lib.groups():
            self.go("gear")  # its last piece moved out, so the group is gone
            return
        view, kind = self.view_key, kind_of(self.view_key)
        self.sidebar.refresh()
        pkg = self.packages.pkg
        open_kit = f"kit:{pkg.id}" if pkg is not None and view == "kits" and self.dock.opened else ""
        self.sidebar.select(open_kit if open_kit in self.sidebar.rows else view)
        self.items.earned = None  # (worked out again below, on a gear page; the panel works it out otherwise)
        if kind == "gear":
            self.gear_table.fill(lib, b, self._grp(), self._divide_for(view))
            self.items.earned = self.gear_table.earned  # worked out once a refresh, for the piece's panel too
            page = self.gear_table if lib.items else self._empty_page("gear")
            self.btn_export.setVisible(bool(lib.items))  # the share button: once there's gear to print
        elif kind == "packages":
            self.kit_table.fill(lib, b)
            page = self.kit_table if lib.packages else self._empty_page("packages")
        elif view == "calendar":
            self.calendar.fill(lib)
            page = self.cal_scroll
        else:
            self.rental_table.fill(lib, view if view in ("out", "upcoming") else "all")
            page = self.rental_table if self.rental_table.topLevelItemCount() else self._empty_page(view)
        self.pages.setCurrentWidget(page)
        empty = page is self.empty  # nothing to search or filter
        self.search.setVisible(view != "calendar" and not empty)
        self.view_menu.setVisible(kind == "gear" and not empty)
        if empty and not self.assistant_showing():
            self.dock.set_open(False)
        self._apply_search()
        if self.history is not None:
            self.history.mark()

    def _into_list(self, open_it: bool = False) -> None:
        """From the search to the list: the keyboard moves on to the first row showing (`open_it`: open it)."""
        t = self._table()
        rows = list(t.showing_rows()) if t is not None else []
        if not rows:
            return
        row = t.currentItem() if t.currentItem() in rows else rows[0]
        if open_it or t.currentItem() is not row:
            t.setCurrentItem(row)
        t.setFocus()

    def _scanned(self) -> None:
        """A scanner types a label's code and presses Return: open that piece. Return on words you typed opens
        the first match."""
        item_id = document.item_from_code(self.search.text())
        if item_id is None:
            if self.search.text().strip():
                self._into_list(open_it=True)
            return
        self.search.clear()
        if item_id in self.lib.items:
            self.open("gear", item_id)
        else:
            self.toast("That label's piece isn't in Bodega anymore.", "problem")

    def _apply_search(self) -> None:
        t = self._table()
        self.totals.setVisible(t is self.gear_table and bool(self.lib.items))
        if t is None:
            self.count.set_full_text("")
            self.no_results.hide()
            self.filter_chips.show_for(None)
            return
        text = self.search.text()
        filtered = t is self.gear_table and self.view_menu.filter.active()
        self.filter_chips.show_for(self.view_menu.filter if filtered else None)
        if t is self.gear_table:
            shown = t.show_only(text, self.view_menu.filter.keep(self.lib))
            self._totals(shown)
            n = len(shown)
        elif text.strip():
            n = t.filter(text)
        else:
            n = sum(1 for i in range(t.topLevelItemCount()) if not t.topLevelItem(i).isHidden())
        self.count.set_full_text(f"{n:,}" if n else "")
        if n == 0 and t.topLevelItemCount() and (text.strip() or filtered):
            self.no_results.show_over(t, text)
        else:
            self.no_results.hide()

    def _mark_assistant(self) -> None:
        """The assistant's button is on while the assistant is open."""
        if hasattr(self, "btn_ai"):
            self.btn_ai.setChecked(self.assistant_showing())

    def _columns_changed(self, hidden: list[str]) -> None:
        """A column shown or hidden (kept for next time); Earned, shown again, is worked out again."""
        self.lib.settings["hidden_columns"] = hidden
        if "earned" not in hidden and self.gear_table.earned is None:
            self.refresh()

    def _filter_off(self, what: str, key: str) -> None:
        """A filter chip's ✕: that filter comes off (the others stay)."""
        f = self.view_menu.filter
        if what == "show":
            f.show = "all"
        elif what == "company":
            f.company = ""
        else:
            f.missing.discard(key)
        self.view_menu.show_state()
        self.view_menu.changed.emit()

    def _clear_hiding(self, what: str) -> None:
        """No Results' button: the search, or the filters, put back."""
        if what == "search":
            self.search.clear()
        else:
            self.view_menu.clear()
            self.view_menu.changed.emit()

    def _totals(self, shown: list[str]) -> None:
        """The bar under the gear table: what the gear showing adds up to (every row is one piece)."""
        b = self.lib.pricing()
        stocks = self.gear_table.stocks
        total = pricing.Stock()
        for item_id in shown:
            if item_id in stocks:
                total.add(stocks[item_id])
        cur = (b.currency if b else "$") or "$"
        tax = b.value_tax if b else "0"
        self.total_values["pieces"].setText(f"{total.pieces:,}")
        self.total_values["paid"].setText(money.fmt(total.paid, cur))
        # the totals are short by whatever has no price: say how many, so they aren't read as everything
        unpriced = sum(1 for i in shown if i in self.lib.items and not money.parse(self.lib.items[i].value))
        self.total_labels["paid"].setText(f"Paid · {unpriced:,} not priced" if unpriced else "Paid")
        self.total_labels["paid"].setToolTip("Left out of the totals: no price yet" if unpriced else "")
        self.total_values["tax"].setText(money.fmt(total.tax, cur))
        self.total_labels["tax"].setText(f"Tax {money.fmt_rate(tax)}")
        self.total_values["value"].setText(money.fmt(total.value, cur))
        self.total_values["day"].setText(money.fmt(total.day, cur))

    def _empty_page(self, which: str) -> QWidget:
        if which == "gear":
            self.empty.show_for(
                (
                    ("edit", "Add Manually", "One piece at a time", "", lambda: self.new("gear")),
                    (
                        "table",
                        "Import Spreadsheet…",
                        "Excel or CSV",
                        "Or drop a spreadsheet on this page",
                        self.import_sheet,
                    ),
                    ("link", "Google Sheets…", "From a share link", "", self.import_google),
                ),
                sheet_tile=1,
            )
        elif which == "packages":
            self.empty.show_for((("case", "New Kit", "Gear that rents together", "", lambda: self.new("packages")),))
        else:
            icon = {"out": "camera", "upcoming": "clock", "rentals": "receipt"}[which]
            self.empty.show_for(((icon, "New Rental", "A quote or a booking", "", lambda: self.new("rentals")),))
        return self.empty

    def _inspector_empty(self, kind: str) -> None:
        panel = {"gear": self.items, "packages": self.packages, "rentals": self.rentals}[kind]

        def blank() -> None:
            if kind == "rentals" and not self.lib.businesses:
                panel.show_empty("Add Your Profile", "", "Add Your Profile…", lambda: self.edit_business(True))
            else:
                panel.show_empty("Nothing Selected", "", "", None)
                panel.empty_btn.hide()

        self.dock.after_close(blank)  # it slides away still showing what was picked
        if kind == "gear":
            self.items.it = None
        elif kind == "packages":
            self.packages.pkg = None
            if self.view_key == "kits":
                self.sidebar.select("kits")
        else:
            self.rentals.r = None
        self.dock.set_open(False)

    def escape(self) -> None:
        """Esc closes one layer at a time: the search's words first, then the search itself, then the panel."""
        if self.search.hasFocus():
            if self.search.text():
                self.search.clear()
            else:
                t = self._table()
                (t or self.pages).setFocus()
            return
        self.deselect()

    def deselect(self) -> None:
        """Esc, or a click on empty space: nothing picked, the panel slides away (and a new piece you didn't
        fill in goes away)."""
        self.flush()
        self._drop_fresh()
        t = self._table()
        if t is not None:
            t._quiet = True
            t.clearSelection()
            t.setCurrentItem(None)
            t._quiet = False
        self._inspector_empty(kind_of(self.view_key))

    def _remember_folds(self) -> None:
        self.lib.settings["folded"] = sorted(self.gear_table.folded)

    # Opening
    def open(self, kind: str, obj_id: str) -> None:
        """Open a piece of gear, a kit or a rental on the right (moving to its place if needed)."""
        where = {"gear": self.lib.items, "packages": self.lib.packages, "rentals": self.lib.rentals}[kind]
        if obj_id not in where:  # deleted since (a rental line can still name gear that's gone)
            self.toast("That's been deleted.")
            return
        if kind != kind_of(self.view_key):
            self.flush()
            target = {"gear": "gear", "packages": "kits", "rentals": "rentals"}[kind]
            if kind == "gear":
                it = self.lib.items.get(obj_id)
                self.go(target)
                if it is not None:
                    self.gear_table.select_id(obj_id)
            else:
                self.go(target)
                t = self._table()
                if t is not None:
                    t.select_id(obj_id)
        else:
            t = self._table()
            if t is not None and t.current_id() != obj_id:
                if kind == "gear" and not self._in_table(obj_id) and self.view_key != "gear":
                    self.go("gear")
                (self._table() or t).select_id(obj_id)
        self._load(kind, obj_id)

    def _load(self, kind: str, obj_id: str) -> None:
        self.flush()
        with pricing.indexed(self.lib):
            self._load_now(kind, obj_id)

    def _load_now(self, kind: str, obj_id: str) -> None:
        self._drop_fresh(keep=obj_id)
        # something else opening in a panel starts at its top (not where the last one was scrolled to)
        if kind == "gear":
            it = self.lib.items.get(obj_id)
            if it is not None and (self.items.it is not it or not self.items.form.isVisible()):
                self.items.load(it)
                self.items.to_top()
        elif kind == "packages":
            p = self.lib.packages.get(obj_id)
            if p is not None and (self.packages.pkg is not p or not self.packages.form.isVisible()):
                self.packages.load(p)
                self.packages.to_top()
        else:
            r = self.lib.rentals.get(obj_id)
            if r is not None:
                if r.business_id not in self.lib.businesses and self.lib.businesses:
                    r.business_id = next(iter(self.lib.businesses))
                if self.rentals.r is not r or not self.rentals.form.isVisible():
                    self.rentals.load(r)
                    self.rentals.to_top()
        self.inspector.setCurrentWidget({"gear": self.items, "packages": self.packages}.get(kind, self.rentals))
        if kind == "packages" and self.view_key == "kits":  # the kit's own row in the sidebar
            self.sidebar.select(f"kit:{obj_id}" if f"kit:{obj_id}" in self.sidebar.rows else "kits")
        self.dock.set_open(True)

    def _row_menu(self, kind: str, obj_id: str, pos) -> None:
        if kind == "gear":
            ids = self.gear_table.selected_ids()
            if obj_id not in ids:
                ids = [obj_id]
            m = QMenu(self)
            n = len(ids)
            m.addAction(  # a list to search, once this menu has closed (never a menu over a menu)
                theme.menu_icon("folder"),
                "Move To…" if n == 1 else f"Move {n} To…",
                lambda: QTimer.singleShot(0, self, lambda: self.move_to(ids)),
            )
            m.addAction(theme.menu_icon("arrow-up"), "Move Up", lambda: self.step_gear(-1, ids))
            m.addAction(theme.menu_icon("arrow-down"), "Move Down", lambda: self.step_gear(1, ids))
            m.addSeparator()
            if len(ids) == 1:
                it = self.lib.items.get(obj_id)
                m.addAction(theme.menu_icon("copy"), "Duplicate", lambda: self.duplicate(kind, obj_id))
                if it is not None and it.parent:
                    m.addAction(theme.menu_icon("unlink"), "Make It Its Own Piece", lambda: self.detach(obj_id))
                m.addAction(
                    theme.menu_icon("receipt"),
                    "Rent This",
                    lambda: (self.open("gear", obj_id), self.rent_this()),
                )
                m.addAction(theme.menu_icon("assistant"), "Update with AI", lambda: self.ai_this_piece(obj_id))
                m.addSeparator()
                m.addAction(theme.menu_icon("trash"), "Delete…", lambda: self.delete(kind, obj_id))
            else:
                m.addAction(theme.menu_icon("trash"), f"Delete {len(ids)}…", lambda: self.delete_gear(ids))
            m.exec(pos)
            return
        items = [("copy", "Duplicate", lambda: self.duplicate(kind, obj_id))]
        if kind == "rentals":  # the same commands as the rental's own ⋯ (and its Agreement…)
            items += [
                ("file", "Agreement…", lambda: self.show_pages(("rental", obj_id))),
                ("calendar", "Add to Calendar", lambda: self.add_to_calendar(obj_id)),
                ("check", "Check Out…", lambda: self.check_rental(obj_id, False)),
                ("check", "Check In…", lambda: self.check_rental(obj_id, True)),
                ("receipt", "Send to Saldo…", lambda: self.send_to_saldo(obj_id)),
            ]
            r = self.lib.rentals.get(obj_id)
            if r is not None and not r.deletable():  # a booked rental is cancelled, never deleted
                if not r.is_cancelled():
                    items += [("", "-", None), ("x", "Mark as Cancelled…", lambda: self.cancel_rental(r))]
                menu(self, items).exec(pos)
                return
        items += [("", "-", None), ("trash", "Delete…", lambda: self.delete(kind, obj_id))]
        menu(self, items).exec(pos)

    # Groups

    # Settings

    # New, duplicate, delete

    # Attaching

    # Kits + rentals: adding gear

    # Edits

    # Renters

    # Profiles

    # Import / export

    # The page window

    # Updates

    # Misc
    def toast(self, text: str, tone: str = "") -> None:
        """A short message over the page. `tone`: "done" (it worked), "problem" (it didn't: say what to do),
        or "" for news."""
        self.toaster.show_message(text, tone)
        self._clear_of_toast()

    def _clear_of_toast(self) -> None:
        """A toast never hides the row you're on: the table scrolls it clear (the toast floats at the bottom)."""
        t = self._table()
        row = t.currentItem() if t is not None else None
        if row is None or not self.toaster.isVisible():
            return
        rect = t.visualItemRect(row)
        on_window = QRect(t.viewport().mapTo(self, rect.topLeft()), rect.size())
        if on_window.intersects(self.toaster.geometry()):
            t.scrollToItem(row, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _toast_area(self) -> QRect:
        """Where toasts float: centred over the page, between the side panels, above the totals."""
        return QRect(self.pages.mapTo(self, QPoint(0, 0)), self.pages.size())

    def show(self) -> None:
        """The first time: filling the screen (all of it but the menu bar and Dock). After that: the size
        and place you left it, if it still fits a screen you have (else filling the screen again)."""
        if self._restored:
            super().show()
            return
        geo = self.lib.settings.get("geometry")
        if isinstance(geo, str) and geo and self._fits_after(geo):
            super().show()
        elif self.titlebar is not None:  # the Mac: fill the free area ourselves (zooming is unreliable here)
            titlebar.fill_screen(self)
            super().show()
        else:
            self.showMaximized()

    def _fits_after(self, geo: str) -> bool:
        """Put the window back where it was; True if that lands wholly on a screen."""
        try:
            if not self.restoreGeometry(QByteArray.fromHex(geo.encode())):
                return False
        except (TypeError, ValueError):
            return False
        frame = self.frameGeometry()
        return any(s.availableGeometry().adjusted(-2, -2, 2, 2).contains(frame) for s in QGuiApplication.screens())

    def resizeEvent(self, e):
        """The inspector gives up some width on a smaller window, so the toolbar never crowds."""
        super().resizeEvent(e)
        w = max(tokens.INSPECTOR_MIN, min(tokens.INSPECTOR_W, int(self.width() * tokens.INSPECTOR_SHARE)))
        self.dock.set_target(w)
        for i in range(self.inspector.count()):  # every right-hand panel, whatever it is
            self.inspector.widget(i).setFixedWidth(w)
        if self.toaster.isVisible():
            self.toaster.place()

    def _let_work_finish(self) -> None:
        """A price check or update check may still be waiting on a website. Give it a moment; if it's still
        busy, quit without waiting for it (everything's saved by now), instead of crashing on the way out."""
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        self.assistant.shutdown()
        busy = [t for t in self.findChildren(QThread) if t.isRunning()]
        for t in busy:
            t.wait(tokens.QUIT_WAIT_MS)
        if any(t.isRunning() for t in busy):
            log.info("quitting while a download is still running")
            QApplication.instance().setProperty("exit_now", True)

    def showEvent(self, e):
        super().showEvent(e)
        if self.titlebar is not None:
            QTimer.singleShot(0, self.titlebar.fit)

    def _say_newer_format(self) -> None:
        from bodega.ui.dialogs.common import notice

        notice(
            self,
            "Saved by a Newer Bodega",
            "Your gear and rentals were last saved by a newer version of Bodega. Update Bodega to see everything; "
            "until then, what the newer version added is kept just as it was.",
        )

    def closeEvent(self, e):
        if not self.may_quit():
            e.ignore()
            return
        self.shutdown()
        super().closeEvent(e)

    def _jobs_running(self) -> str:
        """What's still working in the background ('' if nothing): an AI job, or a photo coming from a link."""
        if self.assistant.running():
            return "Your AI is still working on a job"
        job = self.items._photo_job
        if job is not None and job.isRunning():
            return "A photo is still coming from its link"
        return ""

    def may_quit(self) -> bool:
        """Quitting over changes that couldn't be saved asks first: Try Again, Quit Anyway or Cancel. So does
        quitting while a job runs in the background: what it finds would be lost."""
        from bodega.ui.dialogs.common import Alert, confirm

        busy = self._jobs_running()
        if busy and not confirm(
            self,
            "Stop and Quit?",
            f"{busy}. If you quit now, what it found so far is lost.",
            "Stop and Quit",
        ):
            return False
        while True:
            self.flush()
            if not self.lib.unsaved:
                return True
            why = (self.lib.why_unsaved or ("Bodega can't write to its folder", ""))[0]
            answer = Alert(
                self,
                "Quit Without Saving?",
                f"Your latest changes aren't saved: {why}. If you quit now, they're lost.",
                "Try Again",
                "Cancel",
                other="Quit Anyway",
            ).exec()
            if answer == Alert.OTHER:
                log.warning("quit with unsaved changes: %s", ", ".join(sorted(self.lib.unsaved)))
                return True
            if answer != Alert.DialogCode.Accepted:
                return False

    def shutdown(self) -> None:
        """Save everything before quitting (and the window's size and place for next time)."""
        self.flush()
        if not self._restored:
            self.lib.settings["geometry"] = bytes(self.saveGeometry().toHex()).decode()
        self._let_work_finish()
        try:
            self.lib.save_settings()
        except OSError:
            log.warning("couldn't save settings", exc_info=True)
