"""Provisioned EasyOCR with an explicit fix for the 1.7.2 Tamil alphabet.

The official 1.7.2 config's Tamil alphabet is a truncated ordered prefix of its
own ta_char.txt. The shipped checkpoint has 143 CTC output classes (142 symbols
plus blank). Restore the full shipped alphabet only for that exact known shape;
never truncate checkpoint weights or guess an arbitrary character order.
Upstream: https://github.com/JaidedAI/EasyOCR/tree/v1.7.2/easyocr
"""
import os
from pathlib import Path
import string


def reader(*, download=False):
    import easyocr
    from easyocr.config import recognition_models
    languages = os.getenv('FARMSYNC_OCR_LANGUAGES', 'ta,en').split(',')
    if 'ta' in languages:
        model = recognition_models['gen1']['tamil_g1']
        chars = ''.join((Path(easyocr.__file__).parent/'character/ta_char.txt').read_text(encoding='utf-8').splitlines())
        expected = model['symbols'] + string.ascii_lowercase + string.ascii_uppercase + chars
        actual = model['characters']
        if len(expected) != 142 or len(actual) not in {126, 142} or not expected.startswith(actual):
            raise RuntimeError('Unrecognized Tamil OCR alphabet; explicit model compatibility validation required')
        model['characters'] = expected
    return easyocr.Reader(languages, gpu=False, verbose=False, download_enabled=download, model_storage_directory=os.getenv('FARMSYNC_OCR_MODEL_DIR', '.runtime/models/easyocr'))
