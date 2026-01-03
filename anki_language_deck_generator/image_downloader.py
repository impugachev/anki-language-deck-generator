import logging
import time
from pathlib import Path
from icrawler.builtin import BingImageCrawler


class ImageDownloader:
    def __init__(self, working_dir):
        self.working_dir = Path(working_dir)

    def download_image(self, word):
        for _ in range(5):
            try:
                BingImageCrawler(
                    storage={'root_dir': str(self.working_dir)},
                    log_level=logging.ERROR
                ).crawl(
                    keyword=word,
                    max_num=1,
                    overwrite=True
                )
                break
            except Exception:
                time.sleep(1)
                continue
        else:
            raise RuntimeError(f"Cannot find an image for the word '{word}'")
        image_file = next(self.working_dir.glob('000001.*'))
        new_name = self.working_dir / word / f'{word}{image_file.suffix}'
        image_file.rename(new_name)
        return new_name
