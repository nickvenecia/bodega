"""(The standard's AI-30) Each real AI provider, asked once with a key that isn't one: its refusal reads in plain words
and never shows the key. These need the internet, so they run where BODEGA_ONLINE=1 (CI's Linux machine) and are
skipped everywhere else. Nothing is billed: the question is the provider's list of models."""

from __future__ import annotations

import os
import re

import pytest

from bodega.services.ai.providers import PROVIDERS, AIError, Setup, list_models

pytestmark = [
    pytest.mark.online,
    pytest.mark.skipif(os.environ.get("BODEGA_ONLINE") != "1", reason="needs the internet (BODEGA_ONLINE=1)"),
]

BAD_KEY = "sk-bodega-not-a-real-key-0000"
REAL = sorted(k for k, p in PROVIDERS.items() if p.base_url and p.needs_key)
NOT_PLAIN = re.compile(r"[{}<>\[\]]|Traceback|HTTP Error|urllib|errno|Errno|ssl|SSL|\bNone\b")


@pytest.mark.parametrize("provider", REAL, ids=REAL)
def test_a_bad_key_is_refused_in_plain_words(provider):
    with pytest.raises(AIError) as got:
        list_models(Setup(provider, ""), key=BAD_KEY)
    said = str(got.value)
    assert BAD_KEY not in said and "sk-bodega" not in said, said  # the key never shows
    assert said[:1].isupper() and said.rstrip().endswith((".", "!")), said  # a sentence
    assert not NOT_PLAIN.search(said) and len(said) < 400, said  # words, not the computer's
