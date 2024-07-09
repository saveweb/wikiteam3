import os
import re
import sys
import time
from typing import Any, Dict, Generator

import requests

from wikiteam3.dumpgenerator.exceptions import ExportAbortedError, PageMissingError
from wikiteam3.dumpgenerator.api import handle_StatusCode
from wikiteam3.dumpgenerator.log import log_error
from wikiteam3.dumpgenerator.config import Config
from wikiteam3.utils.util import underscore


HISTORY_MIN_CHUNKSIZE = 2
""" To loop over all the revisions, we need to retrieve at least 2 revisions at a time. """
MAX_SECONDS = 100
""" max seconds to wait in a single sleeping. """

def getXMLPageCore(params: Dict, config: Config, session: requests.Session) -> str:
    """
    returns a XML containing params['limit'] revisions (or current only), ending in </mediawiki>
    if retrieving params['limit'] revisions fails, returns a current only version
    if all fail, returns the empty string
    """
    assert "pages" in params, "pages not in params"
    assert "limit" in params, "limit not in params"

    xml = ""
    c = 0
    maxretries = config.retries  # x retries and skip
    increment_delay = max(config.delay, 1.0)

    while not re.search(r"</mediawiki>", xml):
        if c > 0 and (c < maxretries or params["limit"] > HISTORY_MIN_CHUNKSIZE):
            delay = min(increment_delay * c, MAX_SECONDS) # incremental until MAX_SECONDS
            print(
                f'    In attempt {c}, XML for "{params["pages"]}" is wrong. Waiting {delay} seconds and reloading...'
            )
            time.sleep(delay)
            # reducing server load requesting smallest chunks (if curonly then
            # limit = 1 from mother function)
            if params["limit"] > 1:
                # NOTE: if limit is float and betwennt 0 to 1, the MW backend will force-int it to 0
                new_limit: int = params["limit"] // 2  # half
                if new_limit < HISTORY_MIN_CHUNKSIZE:
                    new_limit = HISTORY_MIN_CHUNKSIZE

                assert new_limit >= HISTORY_MIN_CHUNKSIZE, f"new_limit: {new_limit} < {HISTORY_MIN_CHUNKSIZE}"

                # set new limit
                if new_limit != params["limit"]:
                    print(
                        f'    Reducing the chunksize of revisions to retrieve from {params["limit"]} to {new_limit}'
                    )
                    params["limit"] = new_limit
        if c >= maxretries:
            print("    We have retried %d times" % (c))
            print(
                '    MediaWiki error for "%s", network error or whatever...'
                % (params["pages"])
            )
            if config.failfast:
                print("Exit, it will be for another time")
                sys.exit(1)
            # If it's not already what we tried: our last chance, preserve only the last revision...
            # config.curonly means that the whole dump is configured to save only the last,
            # params['curonly'] should mean that we've already tried this
            # fallback, because it's set by the following if and passed to
            # getXMLPageCore
            if not config.curonly and "curonly" not in params:
                print("    Trying to save only the last revision for this page...")
                params["curonly"] = 1
                log_error(
                    config=config, to_stdout=True,
                    text='Error while retrieving the full history of "%s". Trying to save only the last revision for this page'
                    % (params["pages"]),
                )
                return getXMLPageCore(
                    params=params, config=config, session=session
                )
            else:
                print("    Saving in the errors log, and skipping...")
                log_error(
                    config=config, to_stdout=True,
                    text='Error while retrieving the last revision of "%s". Skipping.'
                    % (params["pages"]),
                )
                raise ExportAbortedError(config.index)
                return ""  # empty xml
        # FIXME HANDLE HTTP Errors HERE
        try:
            r = session.post(
                url=config.index, params=params, timeout=120
            )
            handle_StatusCode(r)
            xml = r.text
        except requests.exceptions.ConnectionError as e:
            print("    Connection error: %s" % (str(e.args[0])))
            xml = ""
        except requests.exceptions.ReadTimeout as e:
            print("    Read timeout: %s" % (str(e.args[0])))
            xml = ""
        c += 1

    return xml


def getXMLPageWithExport(config: Config, title: str,
                         *, verbose=True, session: requests.Session
                         ) -> Generator[str, None, None]:
    """Get the full history (or current only) of a page"""

    # if server errors occurs while retrieving the full page history,
    # it may return [oldest OK versions] + last version, excluding middle revisions,
    # so it would be partialy truncated
    # http://www.mediawiki.org/wiki/Manual_talk:Parameters_to_Special:Export#Parameters_no_longer_in_use.3F

    PARAM_LIMIT = int(os.getenv("PARAM_XML_LIMIT", 1000))
    truncated = False
    title_ = underscore(title)
    # do not convert & into %26, title_ = re.sub('&', '%26', title_)

    params: Dict[str, Any]
    if config.export:
        params = {"title": config.export, "pages": title_, "action": "submit"}
    else:
        params = {"title": "Special:Export", "pages": title_, "action": "submit"}
    if config.curonly:
        params["curonly"] = 1
        params["limit"] = 1
    else:
        params["offset"] = "1"  # 1 always < 2000s
        params["limit"] = PARAM_LIMIT
    # in other case, do not set params['templates']
    if config.templates:
        params["templates"] = 1

    xml = getXMLPageCore(params=params, config=config, session=session)
    if xml == "":
        raise ExportAbortedError(config.index)
    if "</page>" not in xml:
        raise PageMissingError(params["title"], xml)


    yield xml.split("</page>")[0]

    # if complete history, check if this page history has > limit edits, if so, retrieve all using offset if available
    # else, warning about Special:Export truncating large page histories
    r_timestamp = r"<timestamp>([^<]+)</timestamp>"

    edit_count = 0
    edit_count += len(re.findall(r_timestamp, xml))

    # search for timestamps in xml to avoid analysing empty pages like
    # Special:Allpages and the random one
    if not config.curonly and re.search(r_timestamp, xml):
        while not truncated and params["offset"]:  # next chunk
            # get the last timestamp from the acum XML
            params["offset"] = re.findall(r_timestamp, xml)[-1]
            try:
                xml2 = getXMLPageCore(params=params, config=config, session=session)
            except MemoryError:
                print("The page's history exceeds our memory, halving limit.")
                params["limit"] = params["limit"] / 2
                continue

            # are there more edits in this next XML chunk or no <page></page>?
            if re.findall(r_timestamp, xml2):
                if re.findall(r_timestamp, xml2)[-1] == params["offset"]:
                    # again the same XML, this wiki does not support params in
                    # Special:Export, offer complete XML up to X edits (usually
                    # 1000)
                    print(
                        "ATTENTION: This wiki does not allow some parameters in Special:Export, therefore pages with large histories may be truncated"
                    )
                    truncated = True
                    break
                else:
                    """</namespaces>
                    </siteinfo>
                    <page>
                    <title>Main Page</title>
                    <id>15580374</id>
                    <restrictions>edit=sysop:move=sysop</restrictions> (?)
                    <revision>
                        <id>418009832</id>
                        <timestamp>2011-03-09T19:57:06Z</timestamp>
                        <contributor>
                    """
                    # offset is OK in this wiki, merge with the previous chunk
                    # of this page history and continue
                    try:
                        xml2 = xml2.split("</page>")[0]
                        yield "  <revision>" + (
                            "<revision>".join(xml2.split("<revision>")[1:])
                        )
                    except MemoryError:
                        "The page's history exceeds our memory, halving limit."
                        params["limit"] = params["limit"] / 2
                        continue
                    xml = xml2
                    edit_count += len(re.findall(r_timestamp, xml))
            else:
                params["offset"] = ""  # no more edits in this page history
    yield "</page>\n"

    if verbose:
        if edit_count == 1:
            print("    %s, 1 edit" % (title.strip()))
        else:
            print("    %s, %d edits" % (title.strip(), edit_count))
