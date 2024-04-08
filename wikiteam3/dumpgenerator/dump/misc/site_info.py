import json
import os
import sys
from typing import Optional

import requests

from wikiteam3.dumpgenerator.cli import Delay
from wikiteam3.dumpgenerator.api import get_JSON
from wikiteam3.dumpgenerator.config import Config, OtherConfig


def save_siteinfo(config: Config, session: requests.Session):
    if os.path.exists("%s/siteinfo.json" % (config.path)):
        print("siteinfo.json exists, do not overwrite")
        return

    print("Downloading site info as siteinfo.json")

    result = get_siteinfo(config, session)
    with open(
        "%s/siteinfo.json" % (config.path), "w", encoding="utf-8"
    ) as outfile:
        outfile.write(json.dumps(result, indent=4, sort_keys=True, ensure_ascii=False))
    Delay(config=config)


def assert_siteinfo(result, other: OtherConfig):
    """ assert_max_edits, assert_max_pages, assert_max_images """

    stats = result["query"]["statistics"] if "query" in result else result["statistics"]

    try:
        assert stats["pages"] <= other.assert_max_pages if other.assert_max_pages is not None else True
        assert stats["images"] <= other.assert_max_images if other.assert_max_images is not None else True
        assert stats["edits"] <= other.assert_max_edits if other.assert_max_edits is not None else True
    except AssertionError:
        import traceback
        traceback.print_exc()
        sys.exit(45)


def get_siteinfo(config: Config, session: requests.Session):
    assert config.api

    # MediaWiki 1.13+
    r = session.get(
        url=config.api,
        params={
            "action": "query",
            "meta": "siteinfo",
            "siprop": "general|namespaces|statistics|dbrepllag|interwikimap|namespacealiases|specialpagealiases|usergroups|extensions|skins|magicwords|fileextensions|rightsinfo",
            "sinumberingroup": 1,
            "format": "json",
        },
        timeout=10,
    )
    # MediaWiki 1.11-1.12
    if "query" not in get_JSON(r):
        r = session.get(
            url=config.api,
            params={
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general|namespaces|statistics|dbrepllag|interwikimap",
                "format": "json",
            },
            timeout=10,
        )
    # MediaWiki 1.8-1.10
    if "query" not in get_JSON(r):
        r = session.get(
            url=config.api,
            params={
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general|namespaces",
                "format": "json",
            },
            timeout=10,
        )
    result = get_JSON(r)

    return result