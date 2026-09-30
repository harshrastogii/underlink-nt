"""Checks the community card says the safe things and nothing unsafe."""
import re

import pytest

from underlink import cards

REQUIRED = [
    "make a voice call",
    "You cannot SMS 000",
    "stay in your shelter",
    "No community has reviewed this card",
]
FORBIDDEN = [
    "go outside to find signal",
    "underlink",
    "vulnerable",
    "disadvantaged",
]


@pytest.fixture(scope="module")
def text():
    # Join wrapped lines so phrases split across lines still match.
    return " ".join(cards.card_strings())


@pytest.mark.parametrize("phrase", REQUIRED)
def test_required_phrase_present(text, phrase):
    assert phrase.lower() in text.lower()


@pytest.mark.parametrize("phrase", FORBIDDEN)
def test_forbidden_phrase_absent(text, phrase):
    assert phrase.lower() not in text.lower()


def test_no_advice_to_text_000(text):
    # "text 000" or "SMS 000" may only appear in a negative ("cannot SMS 000").
    for m in re.finditer(r"(\w+)\s+(text|sms)\s+000", text, re.I):
        assert m.group(1).lower() in {"cannot", "not", "can't"}, m.group(0)


def test_no_relay_keys(text):
    assert not re.search(r"\bR[0-9a-f]{8}\b", text)


def test_cells_match_rules(text):
    rules = cards.load_rules()
    for svc in rules["services"]:
        for _, key in cards.COLUMNS:
            assert cards.cell_word(svc["rules"][key]) in text


def test_pdf_exists_and_small():
    pdf = cards.build()
    assert pdf.exists()
    assert pdf.stat().st_size < 300 * 1024
