from aqt import mw, gui_hooks
from aqt.qt import QAction, qconnect

_lxml_registered = False


def _register_lxml_parser():
    # Anki's bundled BeautifulSoup was imported before the add-on's lxml was on
    # sys.path, so the lxml tree builder (used by icrawler) must be registered
    # by hand. Done lazily: the loaded DLL would otherwise block add-on updates.
    global _lxml_registered
    if _lxml_registered:
        return
    from bs4.builder import register_treebuilders_from, _lxml
    register_treebuilders_from(_lxml)
    _lxml_registered = True


def show_deck_generator():
    # Imported here so that the bundled binary dependencies (lxml, Pillow) are
    # only loaded when the add-on is used, and to avoid circular imports
    _register_lxml_parser()
    from anki_language_deck_generator.dialog import DeckGeneratorDialog
    dialog = DeckGeneratorDialog(mw)
    dialog.exec()

def setup_menu():
    action = QAction("Generate Language Learning Deck...", mw)
    qconnect(action.triggered, show_deck_generator)
    mw.form.menuTools.addAction(action)

# Use the new gui_hooks system
gui_hooks.profile_did_open.append(setup_menu)
