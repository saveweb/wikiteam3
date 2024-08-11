import datetime
import hashlib
from pathlib import Path
import re
import sys
from typing import Optional, Union

from wikiteam3.dumpgenerator.config import Config

ALL_DUMPED_MARK = "all_dumped.mark"
UPLOADED_MARK = 'uploaded_to_IA.mark'
XMLRIVISIONS_INCREMENTAL_DUMP_MARK = 'xmlrevisions_incremental_dump.mark'


def underscore(text: str) -> str:
    """ replace(" ", "_") """
    return text.replace(" ", "_")

def space(text: str) -> str:
    """ replace("_", " ") """
    return text.replace("_", " ")


def clean_HTML(raw: str = "") -> str:
    """Extract only the real wiki content and remove rubbish
    This function is ONLY used to retrieve page titles
    and file names when no API is available
    DO NOT use this function to extract page content"""
    # different "tags" used by different MediaWiki versions to mark where
    # starts and ends content
    if re.search("<!-- bodytext -->", raw):
        raw = raw.split("<!-- bodytext -->")[1].split("<!-- /bodytext -->")[0]
    elif re.search("<!-- start content -->", raw):
        raw = raw.split("<!-- start content -->")[1].split("<!-- end content -->")[0]
    elif re.search("<!-- Begin Content Area -->", raw):
        raw = raw.split("<!-- Begin Content Area -->")[1].split(
            "<!-- End Content Area -->"
        )[0]
    elif re.search("<!-- content -->", raw):
        raw = raw.split("<!-- content -->")[1].split("<!-- mw_content -->")[0]
    elif re.search(r'<article id="WikiaMainContent" class="WikiaMainContent">', raw):
        raw = raw.split('<article id="WikiaMainContent" class="WikiaMainContent">')[
            1
        ].split("</article>")[0]
    elif re.search("<body class=", raw):
        raw = raw.split("<body class=")[1].split('<div class="printfooter">')[0]
    else:
        print(raw[:250])
        print("This wiki doesn't use marks to split content")
        sys.exit(1)
    return raw


def undo_HTML_entities(text: str = "") -> str:
    """Undo some HTML codes"""

    # i guess only < > & " ' need conversion
    # http://www.w3schools.com/html/html_entities.asp
    text = re.sub("&lt;", "<", text)
    text = re.sub("&gt;", ">", text)
    text = re.sub("&amp;", "&", text)
    text = re.sub("&quot;", '"', text)
    text = re.sub("&#039;", "'", text)

    return text


def remove_IP(raw: str = "") -> str:
    """Remove IP from HTML comments <!-- -->"""

    raw = re.sub(r"\d+\.\d+\.\d+\.\d+", "0.0.0.0", raw)
    # http://www.juniper.net/techpubs/software/erx/erx50x/swconfig-routing-vol1/html/ipv6-config5.html
    # weird cases as :: are not included
    raw = re.sub(
        r"(?i)[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}:[\da-f]{0,4}",
        "0:0:0:0:0:0:0:0",
        raw,
    )

    return raw


def clean_XML(xml: str = "") -> str:
    """Trim redundant info from the XML however it comes"""
    # do not touch XML codification, leave AS IS

    if re.search(r"</siteinfo>\n", xml):
        xml = xml.split("</siteinfo>\n")[1]
    if re.search(r"</mediawiki>", xml):
        xml = xml.split("</mediawiki>")[0]
    return xml


def sha1bytes(data: bytes) -> str:
    """ return `hashlib.sha1(data).hexdigest()` """
    return hashlib.sha1(data).hexdigest()


def sha1sum(path: Union[str, Path]) -> str:
    """ Return the SHA1 hash of a file """
    if isinstance(path, str):
        path = Path(path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"File {path} does not exist or is not a file")

    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def mark_as_done(config: Config, mark: str, msg: Optional[str] = None):
    done_path = f"{config.path}/{mark}"
    if Path(done_path).exists():
        return
    with open(done_path, "w") as f:
        today = datetime.datetime.isoformat(datetime.datetime.now(datetime.timezone.utc))
        f.write(f"{today}: {msg or ''}\n")

    return True

def is_markfile_exists(config: Config, mark: str) -> bool:
    return (Path(config.path)/ mark).exists()

def int_or_zero(size: Union[int, str]) -> int:
    return int(size) if (
                size
                and (
                    (isinstance(size, str) and size.isdigit())
                    or
                    (isinstance(size, int))
                )
            ) else 0

def is_empty_dir(path: Union[str, Path]) -> bool:
    assert Path(path).is_dir()
    return not any(Path(path).iterdir())
