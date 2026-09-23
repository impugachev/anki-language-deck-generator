"""Offline tests: only the 'Nederlands' section of a Wiktionary page may be read."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from anki_language_deck_generator.dutch_wiktionary import DutchWiktionaryWord, WordNotFoundError


def heading(level, id_, text):
    # current MediaWiki markup: every heading is wrapped in <div class="mw-heading">
    return f'<div class="mw-heading mw-heading{level}"><h{level} id="{id_}">{text}</h{level}></div>'


GENUS_NEUTER = (
    '<a href="/wiki/WikiWoordenboek:Genus" title="WikiWoordenboek:Genus"><span>o</span></a>'
)

# Shaped like nl.wiktionary.org/wiki/sinds: a Dutch preposition, then a Danish neuter noun
SINDS_PAGE = (
    '<div class="mw-parser-output">'
    + heading(2, 'Nederlands', 'Nederlands')
    + heading(4, 'Voorzetsel', 'Voorzetsel')
    + '<p><b>sinds</b></p>'
    + heading(2, 'Deens', 'Deens')
    + heading(4, 'Zelfstandig_naamwoord', 'Zelfstandig naamwoord')
    + '<p><b>sinds</b> ' + GENUS_NEUTER + '</p>'
    + '</div>'
)

DANISH_ONLY_PAGE = (
    '<div class="mw-parser-output">'
    + heading(2, 'Deens', 'Deens')
    + heading(4, 'Zelfstandig_naamwoord', 'Zelfstandig naamwoord')
    + '<p><b>sinds</b> ' + GENUS_NEUTER + '</p>'
    + '</div>'
)

DUTCH_NOUN_PAGE = (
    '<div class="mw-parser-output">'
    + heading(2, 'Nederlands', 'Nederlands')
    + heading(4, 'Zelfstandig_naamwoord', 'Zelfstandig naamwoord')
    + '<p><b>huis</b> ' + GENUS_NEUTER + '</p>'
    + heading(2, 'Engels', 'Engels')
    + heading(4, 'Werkwoord', 'Werkwoord')
    + '</div>'
)


def session_returning(html):
    session = MagicMock()
    session.get.return_value = SimpleNamespace(
        status_code=200,
        headers={},
        json=lambda: {'parse': {'text': html, 'langlinks': []}},
    )
    return session


def test_only_the_dutch_section_is_read(tmp_path):
    word = DutchWiktionaryWord('sinds', tmp_path, session=session_returning(SINDS_PAGE))

    assert word.try_get_part_of_speech() == 'voorzetsel'
    assert word.try_get_article() is None


def test_page_without_dutch_section_is_not_found(tmp_path):
    with pytest.raises(WordNotFoundError, match='no Dutch'):
        DutchWiktionaryWord('sinds', tmp_path, session=session_returning(DANISH_ONLY_PAGE))


def test_dutch_noun_still_gets_its_article(tmp_path):
    word = DutchWiktionaryWord('huis', tmp_path, session=session_returning(DUTCH_NOUN_PAGE))

    assert word.try_get_article() == 'het'
    assert word.try_get_part_of_speech() == 'zelfstandig naamwoord'
