import pytest
from bs4 import BeautifulSoup
from anki_language_deck_generator.dutch_wiktionary import DutchWiktionaryWord, WordNotFoundError


@pytest.fixture
def huis_word(tmp_path):
    return DutchWiktionaryWord('huis', tmp_path)


def test_init_success(huis_word):
    assert huis_word.word == 'huis'
    assert isinstance(huis_word.translations, list)
    assert isinstance(huis_word.soup, BeautifulSoup)


def test_init_word_not_found(tmp_path):
    with pytest.raises(WordNotFoundError):
        DutchWiktionaryWord('thisworddoesnotexist1234567890', tmp_path)


def test_try_get_sound_file_url(huis_word):
    url = huis_word.try_get_sound_file_url()
    assert url is not None
    assert url.startswith('https://upload.wikimedia.org/')


def test_try_get_image_url(huis_word):
    url = huis_word.try_get_image_url()
    assert url is not None
    assert url.startswith(('https://upload.wikimedia.org/', 'https://thumb.wikimedia.org/'))


def test_try_get_transcription(huis_word):
    ipa = huis_word.try_get_transcription()
    assert ipa == '/ɦœʏ̯s/'


def test_try_get_article(huis_word):
    article = huis_word.try_get_article()
    assert article == 'het'


def test_try_get_part_of_speech(huis_word):
    pos = huis_word.try_get_part_of_speech()
    assert pos == 'zelfstandig naamwoord'


def test_try_get_plural_form(huis_word):
    plural = huis_word.try_get_plural_form()
    assert plural == 'huizen'


def test_try_download_sound(huis_word):
    path = huis_word.try_download_sound()
    assert path is not None
    assert path.exists()


def test_try_download_image(huis_word):
    path = huis_word.try_download_image()
    assert path is not None
    assert path.exists()


def test_article_ignores_other_language_sections(tmp_path):
    # 'sinds' is a Dutch preposition; the page also has a Danish neuter noun section
    word = DutchWiktionaryWord('sinds', tmp_path)
    assert word.try_get_part_of_speech() == 'voorzetsel'
    assert word.try_get_article() is None
