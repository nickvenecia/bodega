"""Search: case and accents never stop a match."""

from bodega.core import search


def test_search_ignores_case_and_accents():
    assert search.folded("Café Señor ARRI") == "cafe senor arri"
    hay = search.folded("Arri Alexa Mini — Café Lens Kit")
    assert search.matches(hay, search.words("cafe ALEXA")) and not search.matches(hay, search.words("venice"))
