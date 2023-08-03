import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

from wikiteam3.dumpgenerator.config import Config


def main():
    parser = argparse.ArgumentParser(prog="launcher")

    parser.add_argument("wikispath")
    parser.add_argument("--7z-path", dest="path7z", metavar="path-to-7z")
    parser.add_argument("--generator-arg", "-g", dest="generator_args", action='append')

    args = parser.parse_args()

    wikispath = args.wikispath

from typing import 
    # Basic integrity check for the xml. The script doesn't actually do anything, so you should check if it's broken. Nothing can be done anyway, but redownloading.
    subprocess.call(
        'grep "<title>" *.xml -c;grep "<page>" *.xml -c;grep "</page>" *.xml -c;grep "<revision>" *.xml -c;grep "</revision>" *.xml -c',
        shell=True,
    )

    pathHistoryTmp = Path("..", prefix + "-history.xml.7z.tmp")
    pathHistoryFinal = Path("..", prefix + "-history.xml.7z")
    pathFullTmp = Path("..", prefix + "-wikidump.7z.tmp")
    pathFullFinal = Path("..", prefix + "-wikidump.7z")

    # Make a non-solid archive with all the text and metadata at default compression. You can also add config.txt if you don't care about your computer and user names being published or you don't use full paths so that they're not stored in it.
    compressed = subprocess.call(
        [
            path7z,
            "a",
            "-ms=off",
            "--",
            str(pathHistoryTmp),
            f"{prefix}-history.xml",
            f"{prefix}-titles.txt",
            "index.html",
            "SpecialVersion.html",
            "errors.log",
            "siteinfo.json",
        ],
        shell=False,
    )
    if compressed < 2:
        pathHistoryTmp.rename(pathHistoryFinal)
    else:
        print("ERROR: Compression failed, will have to retry next time")
        pathHistoryTmp.unlink()

    # Now we add the images, if there are some, to create another archive, without recompressing everything, at the min compression rate, higher doesn't compress images much more.
    shutil.copy(pathHistoryFinal, pathFullTmp)

    subprocess.call(
        [
            path7z,
            "a",
            "-ms=off",
            "-mx=1",
            "--",
            str(pathFullTmp),
            f"{prefix}-images.txt",
            "images/",
        ],
        shell=False,
    )

    pathFullTmp.rename(pathFullFinal)

    os.chdir("..")
    print("Changed directory to", os.getcwd())
    time.sleep(1)


if __name__ == "__main__":
    main()
