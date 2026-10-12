"""Looking after gear: the log and service reminders."""

from __future__ import annotations

from datetime import date

from bodega.core import maintenance, sample
from bodega.core.model import Item, LogEntry
from bodega.core.store import Library


def test_due_from_the_last_service():
    it = Item(service_days=90, created="2026-01-01T09:00:00")
    assert maintenance.due(it, date(2026, 3, 1)).state == "ok"
    assert maintenance.due(it, date(2026, 3, 25)).state == "soon"
    late = maintenance.due(it, date(2026, 4, 10))
    assert late.state == "overdue" and late.days < 0 and "Overdue" in maintenance.say(late)
    it.log.append(LogEntry("2026-04-01", "service", "Cleaned the sensor"))
    it.log.append(LogEntry("2026-04-05", "repair", "New fan"))  # repairs don't reset the clock
    assert maintenance.due(it, date(2026, 4, 10)).when == date(2026, 6, 30)
    assert maintenance.due(Item(), date(2026, 1, 1)) is None
    assert maintenance.due(Item(service_days=30, status="retired")) is None


def test_log_round_trips_and_tolerates_junk():
    it = Item(log=[LogEntry("2026-04-01", "service", "Clean", "40")], service_days=180)
    back = Item.from_dict(it.to_dict())
    assert back.log == it.log and back.service_days == 180
    odd = Item.from_dict({"log": [{"kind": "explode", "text": 5}, "nope"], "service_days": "lots"})
    assert odd.log[0].kind == "note" and odd.service_days == 0


def test_maintenance_in_the_panel(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    it = next(iter(win.lib.items.values()))
    win.open("gear", it.id)
    p = win.items
    p._add_part("care")
    p.every.setCurrentIndex(p.every.findData("90"))
    assert it.service_days == 90 and p.due.isVisibleTo(p)
    p.log_text.setText("Cleaned the sensor")
    p._log_add()
    assert it.log and it.log[-1].kind == "service" and p.log_box.isVisibleTo(p)
    win.flush()
    assert Library(data_folder).load().items[it.id].log[0].text == "Cleaned the sensor"
    p._log_remove(0)
    assert not it.log
    win.close()
