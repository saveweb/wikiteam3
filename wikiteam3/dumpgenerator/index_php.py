import delay
import os

from clean_html import removeIP


def saveIndexPHP(config={}, session=None):
    """Save index.php as .html, to preserve license details available at the botom of the page"""

    if os.path.exists("%s/index.html" % (config["path"])):
        print("index.html exists, do not overwrite")
    else:
        print("Downloading index.php (Main Page) as index.html")
        r = session.post(url=config["index"], params={}, timeout=10)
        raw = r.text
        delay(config=config, session=session)
        raw = removeIP(raw=raw)
        with open("%s/index.html" % (config["path"]), "wb") as outfile:
            outfile.write(bytes(raw, "utf-8"))