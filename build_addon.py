import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


PLATFORM_INDEPENDENT_PACKAGES = [
    'genanki==0.13.1',
    'icrawler==0.6.10',
    'cached_property==2.0.1',
    'chevron==0.14.0',
    'six==1.17.0',
    'gTTS==2.5.4',
    'deep-translator==1.11.4',
]

BINARY_PACKAGES = [
    'pillow==9.0.1',
    'lxml==4.6.4',
    'pyyaml==6.0.2'
]

PLATFORMS = [
    'win_amd64',
    'win32',
]


def create_addon_package(output_path=None, output_dir=None):
    """Create an Anki addon package

    Args:
        output_path: Path to output .ankiaddon file
        output_dir: Path to output directory for direct addon installation
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # 1. Copy addon_package contents to temp directory
        addon_dir = temp_dir / 'addon'
        shutil.copytree('addon_package', addon_dir, dirs_exist_ok=True)

        # 2. Copy anki_language_deck_generator into addon_package
        def ignore_func(src, names):
            ignored = set()
            # Always ignore 'test' directory at any level
            if 'test' in names:
                ignored.add('test')
            # Ignore '__init__.py' only at the top-level package directory
            if src == 'anki_language_deck_generator' and '__init__.py' in names:
                ignored.add('__init__.py')
            return ignored

        shutil.copytree(
            'anki_language_deck_generator',
            addon_dir / 'anki_language_deck_generator',
            ignore=ignore_func,
            dirs_exist_ok=True
        )

        # 3. Install dependencies
        deps_dir = addon_dir / 'dependencies'
        deps_dir.mkdir(exist_ok=True)
        subprocess.check_call([
            'pip', 'install',
            *PLATFORM_INDEPENDENT_PACKAGES,
            '--no-deps',
            '--target', str(deps_dir)
        ])
        # Download and install binary packages for each platform
        for platform in PLATFORMS:
            plat_dir = deps_dir / 'platform' / platform
            plat_dir.mkdir(parents=True, exist_ok=True)
            subprocess.check_call([
                'pip', 'install',
                *BINARY_PACKAGES,
                '--only-binary=:all:',
                '--platform', platform,
                '--implementation=cp',
                '--python-version', '3.9',
                '--no-deps',
                '--target', str(plat_dir)
            ])

        if output_dir:
            output_dir = Path(output_dir)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            shutil.copytree(addon_dir, output_dir, dirs_exist_ok=True)
            return

        # 4. Create zip file
        output_path = Path(output_path)
        if output_path.exists():
            output_path.unlink()

        # Create the zip file from the addon directory
        shutil.make_archive(str(output_path.with_suffix('')), 'zip', addon_dir)

        # Rename .zip to .ankiaddon if needed
        if output_path.suffix == '.ankiaddon':
            zip_path = output_path.with_suffix('.zip')
            zip_path.rename(output_path)


def main():
    parser = argparse.ArgumentParser(description='Build Anki addon package')

    # Create mutually exclusive group for output options
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        '-o', '--output',
        default='anki_language_deck_generator.ankiaddon',
        help='Output path for the addon package'
    )
    output_group.add_argument(
        '-d', '--output-dir',
        help='Output directory for direct addon installation'
    )

    args = parser.parse_args()

    create_addon_package(
        output_path=args.output if not args.output_dir else None,
        output_dir=args.output_dir
    )

    if args.output_dir:
        print(f'Addon files created in directory: {args.output_dir}')
    else:
        print(f'Addon package created at: {args.output}')


if __name__ == '__main__':
    main()
