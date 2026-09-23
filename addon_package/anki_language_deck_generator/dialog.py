from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QLineEdit, QProgressBar
)
from aqt.utils import showInfo
from anki.utils import int_time
from anki.collection import ImportAnkiPackageRequest, ImportAnkiPackageOptions
from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition
from anki_language_deck_generator.language_codes import LANGUAGES
from anki_language_deck_generator.deck_generator import AnkiDeckGenerator, format_report

import tempfile
import json
from pathlib import Path


class DeckGeneratorDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(parent=main_window)
        self.main_window = main_window
        self.config = self._load_config()
        self.setup_ui()

    @staticmethod
    def _get_config_path():
        return Path(__file__).parent.parent / 'config.json'

    def _load_config(self):
        with self._get_config_path().open('r', encoding='utf-8') as f:
            config = json.load(f)
        return config

    def _save_config(self, source_language, target_language, deck_name):
        config = {
            'default_source_language': source_language,
            'default_target_language': target_language,
            'default_deck_name': deck_name
        }
        with self._get_config_path().open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

    def setup_ui(self):
        self.setWindowTitle('Language Deck Generator')
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Source Language
        source_layout = QHBoxLayout()
        source_label = QLabel('Source Language:')
        self.source_combo = QComboBox()
        self.source_combo.addItems(sorted(LANGUAGES.keys()))
        default_source = self.config.get('default_source_language')
        self.source_combo.setCurrentText(default_source)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        layout.addLayout(source_layout)

        # Target Language
        target_layout = QHBoxLayout()
        target_label = QLabel('Target Language:')
        self.target_combo = QComboBox()
        self.target_combo.addItems(sorted(LANGUAGES.keys()))
        default_target = self.config.get('default_target_language')
        self.target_combo.setCurrentText(default_target)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_combo)
        layout.addLayout(target_layout)

        # Deck Name
        deck_layout = QHBoxLayout()
        deck_label = QLabel('Deck Name:')
        self.deck_name = QLineEdit()
        default_deck = self.config.get('default_deck_name')
        self.deck_name.setText(default_deck)
        deck_layout.addWidget(deck_label)
        deck_layout.addWidget(self.deck_name)
        layout.addLayout(deck_layout)

        # Words Input
        words_label = QLabel('Enter words (one per line):')
        layout.addWidget(words_label)
        self.words_text = QTextEdit()
        layout.addWidget(self.words_text)

        # Progress Bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Buttons
        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        self.generate_btn = QPushButton('Generate Deck')
        self.generate_btn.clicked.connect(self.generate_deck)
        self.generate_btn.setDefault(True)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.generate_btn)
        layout.addLayout(buttons_layout)

    def update_progress(self, current, total):
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f'Processing word {current} of {total} ({percentage}%)')

    def generate_deck(self):
        source_language = self.source_combo.currentText()
        target_language = self.target_combo.currentText()
        deck_name = self.deck_name.text()
        self._save_config(source_language, target_language, deck_name)
        words = [w for w in self.words_text.toPlainText().split('\n') if w.strip()]

        if not words:
            showInfo('Please enter at least one word')
            return

        # Show progress bar and disable generate button
        self.progress_bar.show()
        self.generate_btn.setEnabled(False)

        # Create temporary directory for media files
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                generator = AnkiDeckGenerator(
                    deck_name=deck_name,
                    source_language=source_language,
                    target_language=target_language,
                    working_dir=temp_dir,
                    progress_callback=self.update_progress
                )

                generator.add_words(words)

                # Save to a temporary file
                temp_deck = Path(temp_dir) / f'temp_deck_{int_time()}.apkg'
                generator.save_deck(temp_deck)

                # Import into Anki
                UPDATE_CONDITION = ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER
                self.main_window.col.import_anki_package(
                    ImportAnkiPackageRequest(
                        package_path=str(temp_deck),
                        options=ImportAnkiPackageOptions(
                            update_notes=UPDATE_CONDITION,
                            update_notetypes=UPDATE_CONDITION,
                        )
                    )
                )
                self.main_window.deckBrowser.refresh()

                # Report words that failed or need a check, if any
                if generator.failed_words or generator.warnings:
                    self.show_report_dialog(generator.failed_words, generator.warnings)
                else:
                    showInfo('Deck generated and imported successfully!')
                self.accept()

            except Exception as e:
                showInfo(f'Error generating deck: {str(e)}')
                raise
            finally:
                # Re-enable generate button and hide progress bar
                self.generate_btn.setEnabled(True)
                self.progress_bar.hide()

    def show_report_dialog(self, failed_words, warnings):
        # Failed words with their reasons, plus cards that were created but should be checked.
        # The text is selectable, so the failed words can be copied back into the input.
        dialog = QDialog(self)
        dialog.setWindowTitle('Deck generated with remarks')
        dialog.resize(640, 480)
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        label = QLabel(
            'The deck has been imported, but some words need attention.\n'
            'Words that failed because a service was rate limited (HTTP 429) can simply be '
            're-run later. Re-running a word updates its existing card.'
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(format_report(failed_words, warnings))
        layout.addWidget(text_edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        dialog.exec()
