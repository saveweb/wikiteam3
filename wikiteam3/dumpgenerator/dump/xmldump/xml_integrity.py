from typing import Iterable
from wikiteam3.dumpgenerator.config import Config

def check_XML_integrity(config: Config=None, titles: Iterable[str]=None, session=None):
    """Check XML dump integrity, to detect broken XML chunks"""
    # TODO: Fix XML Integrity Check
    return