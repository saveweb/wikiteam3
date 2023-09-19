import os

from wikiteam3.dumpgenerator.cli import Delay
from wikiteam3.utils import remove_IP
from wikiteam3.dumpgenerator.config import Config

def save_IndexPHP(config: Config, session):
    """Save index.php as .html, to preserve license details available at the botom of the page"""

    assert config.index

    if os.path.exists("%s/index.html" % (config.path)):
        print("index.html exists, do not overwrite")
    else:
        print("Downloading index.php (Main Page) as index.html")
        try:
            r = session.post(url=config.index, params=None, timeout=10)
            raw = str(r.text)
        except Exception as e:
            print("Error: %s" % (e))
            return
        Delay(config=config)
        raw = remove_IP(raw=raw)
        with open("%s/index.html" % (config.path), "w", encoding="utf-8") as outfile:
            outfile.write(raw)
