"""Every page (core/document.py + doc/render.py) builds, lays out and saves."""

from __future__ import annotations

import pytest

from bodega.core import document, sample
from bodega.core.looks import palette
from bodega.core.store import Library


@pytest.fixture
def lib(data_folder):
    return sample.fill(Library(data_folder).load())


def views(lib):
    b = next(iter(lib.businesses.values()))
    r = next(iter(lib.rentals.values()))
    yield document.build_rental(lib, r, b)
    yield document.build_inventory(lib, lib.ordered_items(), b)
    yield document.build_ratecard(lib, lib.ordered_items(), list(lib.packages.values()), b)
    yield document.build_package(lib, next(iter(lib.packages.values())), b)


def test_agreement_groups_by_dates(lib):
    b = next(iter(lib.businesses.values()))
    v = document.build_rental(lib, next(iter(lib.rentals.values())), b)
    heads = [row.cells[1] for row in v.table.rows if row.kind == "subheading"]
    assert len(heads) == 3 and heads[-1] == "Fees"  # two date ranges, then the fee
    assert v.signatures and v.table.checks
    assert any(row.note.startswith("S/N") for row in v.table.rows)


def test_quote_has_no_signatures(lib):
    b = next(iter(lib.businesses.values()))
    r = next(iter(lib.rentals.values()))
    r.status = "quote"
    v = document.build_rental(lib, r, b)
    assert v.title == "Rental Quote" and not v.signatures and not v.table.checks


def test_pages_render_and_save(qapp, lib, tmp_path):
    from bodega.doc import export, render

    for n, v in enumerate(views(lib)):
        for dark in (False, True):
            pages = render.layout(v, palette("blue", dark))
            assert pages and all(p.steps for p in pages)
        pdf = export.to_pdf(render.layout(v, palette("blue")), tmp_path / f"{n}.pdf")
        assert pdf.read_bytes().startswith(b"%PDF")


def test_a_saved_agreement_reads_back_in_another_pdf_reader(qapp, lib, tmp_path):
    from pypdf import PdfReader

    from bodega.core import money, pricing
    from bodega.doc import export, render

    r = next(iter(lib.rentals.values()))
    b = lib.businesses.get(r.business_id) or lib.pricing()
    pdf = export.to_pdf(render.layout(document.build_rental(lib, r, b), palette("blue")), tmp_path / "a.pdf")
    reader = PdfReader(pdf)
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    total = money.fmt(pricing.totals(lib, r, b).total, b.currency or "$")
    for words in (r.number, r.client.company or r.client.name, total, b.name):
        assert words in text, words  # the words are real text: they can be found, copied and read aloud
    assert reader.pages[0].mediabox.width == pytest.approx(612, abs=1)  # Letter, in points
    for n, v in enumerate(views(lib)):  # no page has a letter that copies out as a private symbol
        pdf = export.to_pdf(render.layout(v, palette("blue")), tmp_path / f"{n}.pdf")
        text = "".join(page.extract_text() for page in PdfReader(pdf).pages)
        assert not [ch for ch in text if "\ue000" <= ch <= "\uf8ff"], v.title


def test_a_rentals_summary_for_email_has_its_gear_and_total(lib):
    b = next(iter(lib.businesses.values()))
    text = document.summary_text(lib, next(iter(lib.rentals.values())), b)
    assert "Total:" in text and "FX6 Run & Gun" in text


def test_file_names_are_safe():
    assert document.file_name('A/B: "C"') == "A B C"


def test_counts_read_right_at_one():
    from bodega.core import words

    assert words.count(1, "piece") == "1 piece" and words.count(2, "piece") == "2 pieces"
    assert words.count(1200, "piece") == "1,200 pieces" and words.count(0, "group") == "0 groups"


def test_the_page_window_says_which_page_is_in_view(qapp, lib):
    from dataclasses import replace

    from bodega.doc import render
    from bodega.ui.dialogs.preview import PreviewPanel

    b = lib.pricing()
    many = [replace(it, id=f"{it.id}-{n}") for n in range(12) for it in lib.ordered_items()]
    pages = render.layout(document.build_inventory(lib, many, b), palette("blue"))
    assert len(pages) > 2
    p = PreviewPanel()
    p.resize(900, 700)
    p.show()
    p.set_pages(pages)
    qapp.processEvents()
    assert p.page_of.text() == f"Page 1 of {len(pages)}"
    bar = p.area.verticalScrollBar()
    bar.setValue(bar.maximum())
    assert p.page_of.text() == f"Page {len(pages)} of {len(pages)}"
    p.set_pages(pages[:1])
    assert p.page_of.isHidden()  # one page: nothing to count
    p.deleteLater()
