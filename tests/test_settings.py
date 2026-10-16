"""Every setting is in one list, with its kind and its default (core/settings.py)."""

from __future__ import annotations

import re
from pathlib import Path

from bodega.core import settings


def test_every_setting_bodega_reads_or_writes_is_in_the_one_list():
    root = Path(__file__).resolve().parents[1] / "bodega"
    used = set()
    for f in root.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        used |= set(re.findall(r'settings(?:\.get\(|\[|\.pop\()"([a-z_]+)"', text))
        used |= set(re.findall(r'value\([a-z_.]*settings, "([a-z_]+)"\)', text))
    missing = used - set(settings.DEFAULTS)
    assert not missing, missing  # each one has its kind and default, so no reader makes up its own


def test_a_setting_of_the_wrong_kind_reads_as_its_default():
    assert settings.value({"divide": "group"}, "divide") == {}
    assert settings.value({"hidden_columns": "earned"}, "hidden_columns") is None  # never chosen
    assert settings.value({"hidden_columns": ["earned"]}, "hidden_columns") == ["earned"]
    one, two = settings.value({}, "groups"), settings.value({}, "groups")
    one["gear"] = {}
    assert two == {}  # each reader gets its own copy
