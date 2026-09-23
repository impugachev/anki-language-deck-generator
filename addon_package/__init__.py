import sys
import platform
from pathlib import Path


def _get_architecture():
    bit, system = platform.architecture()
    if system == 'WindowsPE':
        if bit == '64bit':
            return 'win_amd64'
        elif bit == '32bit':
            return 'win32'
        else:
            raise Exception(f'Unsupported platform: {system} {bit}')
    else:
        raise Exception(f'Unsupported platform: {system} {bit}')


def _setup_path():
    addon_dir = Path(__file__).parent
    sys.path.append(str(addon_dir))
    sys.path.insert(0, str(addon_dir / 'dependencies'))
    sys.path.insert(0, str(addon_dir / 'dependencies' / 'platform' / _get_architecture()))


_setup_path()

# Nothing from the bundled binary dependencies (lxml, Pillow) may be imported
# here: Windows cannot delete a loaded DLL, and Anki updates an add-on by
# deleting its folder first. They are loaded when the dialog is opened.
from . import anki_language_deck_generator
