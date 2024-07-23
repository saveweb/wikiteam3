from datetime import datetime
import os
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
import lxml.etree

import mwclient
import mwclient.errors
import requests

from wikiteam3.dumpgenerator.cli.delay import Delay
from wikiteam3.dumpgenerator.exceptions import MWUnknownContentModelException, PageMissingError
from wikiteam3.dumpgenerator.log import log_error
from wikiteam3.dumpgenerator.api.namespaces import getNamespacesAPI
from wikiteam3.dumpgenerator.api.page_titles import read_titles
from wikiteam3.dumpgenerator.dump.page.xmlrev.xml_revisions_page import \
    make_xml_from_page, make_xml_page_from_raw
from wikiteam3.dumpgenerator.config import Config
from wikiteam3.utils.util import XMLRIVISIONS_INCREMENTAL_DUMP_MARK, mark_as_done

ALL_NAMESPACE = -1

def getXMLRevisionsByAllRevisions(config: Config, session: requests.Session, site: mwclient.Site, nscontinue=None, arvcontinue: Optional[str]=None):
    if "all" not in config.namespaces:
        namespaces = config.namespaces
    else:
        # namespaces, namespacenames = getNamespacesAPI(config=config, session=session)
        namespaces = [ALL_NAMESPACE] # magic number refers to "all"

    # <- increasement xmldump
    if env_arvcontinue := os.getenv("ARVCONTINUE", None):
        mark_as_done(config, XMLRIVISIONS_INCREMENTAL_DUMP_MARK)
        print(f"Using [env]ARVCONTINUE={env_arvcontinue}")
        arvcontinue = env_arvcontinue
        print("\n\n[NOTE] DO NOT use wikiteam3uploader to upload incremental xmldump to Internet Archive, we haven't implemented it yet\n\n")
    # ->

    _nscontinue_input = nscontinue
    _arvcontinue_input = arvcontinue
    del nscontinue
    del arvcontinue

    for namespace in namespaces:
        # Skip retrived namespace
        if namespace == ALL_NAMESPACE:
            assert len(namespaces) == 1, \
                "Only one item shoule be there when 'all' namespace are specified"
            _nscontinue_input = None
        else:
            if _nscontinue_input is not None:
                if namespace != _nscontinue_input:
                    print("Skipping already exported namespace: %d" % namespace)
                    continue
                _nscontinue_input = None

        print("Trying to export all revisions from namespace %s" % namespace)
        # arvgeneratexml exists but was deprecated in 1.26 (while arv is from 1.27?!)
        arv_params = {
            "action": "query",
            "list": "allrevisions",
            "arvlimit": config.api_chunksize,
            "arvdir": "newer",
        }
        if namespace != ALL_NAMESPACE:
            arv_params['arvnamespace'] = namespace
        if _arvcontinue_input is not None:
            arv_params['arvcontinue'] = _arvcontinue_input

        if not config.curonly:
            # We have to build the XML manually...
            # Skip flags, presumably needed to add <minor/> which is in the schema.
            # Also missing: parentid and contentformat.
            ARV_PROP = "ids|timestamp|user|userid|size|sha1|contentmodel|comment|content|flags"
            arv_params[
                "arvprop"
            ] = ARV_PROP
            print(
                "Trying to get wikitext from the allrevisions API and to build the XML"
            )
            while True:
                print("[arvcontinue]:", arv_params.get("arvcontinue", ""))
                try:
                    allrevs_response = site.api(
                        http_method=config.http_method, **arv_params
                    )
                    # reset params if the response is OK
                    arv_params["arvprop"] = ARV_PROP
                    if arv_params["arvlimit"] != config.api_chunksize:
                        arv_params["arvlimit"] = min(arv_params["arvlimit"] * 2, config.api_chunksize)
                        print(f"INFO: response is OK, increasing arvlimit to {arv_params['arvlimit']}")
                except mwclient.errors.APIError as e:
                    if e.code == MWUnknownContentModelException.error_code:
                        if arv_params['arvlimit'] != 1:
                            # let's retry with arvlimit=1 to retrieve good revisions as much as possible
                            print("WARNING: API returned MWUnknownContentModelException. retrying with arvlimit=1 (revision by revision)")
                            arv_params["arvlimit"] = 1
                            Delay(config=config)
                            continue
                        elif '|content' in arv_params["arvprop"]:
                            log_error(config=config, to_stdout=True,
                                text=f"ERROR: API returned MWUnknownContentModelException on arvcontinue={arv_params.get('arvcontinue', '')}, " +
                                "retried with arvlimit=1 and still failed. retrying without arvprop=content. " +
                                '(wikiteam3 would mark the revision as "<text deleted="deleted"> in the xmldump)'
                            )
                            arv_params["arvprop"] = ARV_PROP.replace('|content', '')
                            Delay(config=config)
                            continue
                        else:
                            assert False, "This should not happen"
                    else:
                        raise

                except requests.exceptions.HTTPError as e:
                    if (
                            e.response.status_code == 405
                            and config.http_method == "POST"
                    ):
                        print("POST request to the API failed, retrying with GET")
                        config.http_method = "GET"
                        Delay(config=config)
                        continue
                    else:
                        raise
                except requests.exceptions.ReadTimeout as err:
                    # Hopefully temporary, just wait a bit and continue with the same request.
                    # No point putting a limit to retries, we'd need to abort everything.
                    # TODO: reuse the retry logic of the checkAPI phase? Or force mwclient
                    # to use the retry adapter we use for our own requests session?
                    print(f"ERROR: {str(err)}")
                    print("Sleeping for 20 seconds")
                    time.sleep(20)
                    continue
                except mwclient.errors.InvalidResponse as e:
                    if (
                        e.response_text.startswith("<!DOCTYPE html>") # type: ignore
                        and config.http_method == "POST"
                    ):
                        print("POST request to the API failed (got HTML), retrying with GET")
                        config.http_method = "GET"
                        Delay(config=config)
                        continue
                    else:
                        raise

                for page in allrevs_response["query"]["allrevisions"]:
                    yield make_xml_from_page(page, arv_params.get("arvcontinue", ""))

                # find the continue parameter
                if "continue" in allrevs_response:
                    # handle infinite loop
                    if arv_params.get("arvcontinue", None) == allrevs_response["continue"]["arvcontinue"]:
                        allrevs_response = handle_infinite_loop(
                            allrevs_response=allrevs_response, arv_params=arv_params, config=config, site=site
                        )
                    # update continue parameter
                    arv_params["arvcontinue"] = allrevs_response["continue"]["arvcontinue"]
                else:
                    # End of continuation. We are done with this namespace.
                    break

        else: # curonly
            # FIXME: this is not curonly, just different strategy to do all revisions
            # Just cycle through revision IDs and use the XML as is
            print("Trying to list the revisions and to export them one by one")
            # We only need the revision ID, all the rest will come from the raw export
            arv_params["arvprop"] = "ids"
            try:
                allrevs_response = site.api(
                    http_method=config.http_method, **arv_params
                )
            except requests.exceptions.HTTPError as e:
                if (
                        e.response.status_code == 405
                        and config.http_method == "POST"
                ):
                    print("POST request to the API failed, retrying with GET")
                    config.http_method = "GET"
                    raise NotImplementedError("FIXME: here we should retry the same namespace")
                    continue # FIXME: here we should retry the same namespace
                else:
                    raise
            export_params = {
                "action": "query",
                "export": "1",
            }
            # Skip the namespace if it's empty
            if len(allrevs_response["query"]["allrevisions"]) < 1:
                # TODO: log this
                continue
            # Repeat the arvrequest with new arvparams until done
            while True:
                # Reset revision IDs from the previous batch from arv
                revids: List[str] = []
                for page in allrevs_response["query"]["allrevisions"]:
                    for revision in page["revisions"]:
                        revids.append(str(revision["revid"]))
                print(
                    "        %d more revisions listed, until %s"
                    % (len(revids), revids[-1])
                )

                # We can now get the XML for one revision at a time
                # FIXME: we can actually get them in batches as we used to
                # but need to figure out the continuation and avoid that the API
                # chooses to give us only the latest for each page
                for revid in revids:
                    export_params["revids"] = revid
                    try:
                        export_response = site.api(
                            http_method=config.http_method, **export_params
                        )
                    except requests.exceptions.HTTPError as e:
                        if (
                                e.response.status_code == 405
                                and config.http_method == "POST"
                        ):
                            print(
                                "POST request to the API failed, retrying with GET"
                            )
                            config.http_method = "GET"
                            export_response = site.api(
                                http_method=config.http_method, **export_params
                            )
                        else:
                            raise

                    # This gives us a self-standing <mediawiki> element
                    # but we only need the inner <page>: we can live with
                    # duplication and non-ordering of page titles, but the
                    # repeated header is confusing and would not even be valid
                    xml: str = export_response["query"]["export"]["*"]
                    yield make_xml_page_from_raw(xml, arv_params.get("arvcontinue", ""))

                if "continue" in allrevs_response:
                    # Get the new ones
                    # NOTE: don't need to handle infinite loop here, because we are only getting the revids

                    arv_params["arvcontinue"] = allrevs_response["continue"]["arvcontinue"]
                    try:
                        allrevs_response = site.api(
                            http_method=config.http_method, **arv_params
                        )
                    except requests.exceptions.HTTPError as e:
                        if (
                                e.response.status_code == 405
                                and config.http_method == "POST"
                        ):
                            print(
                                "POST request to the API failed, retrying with GET"
                            )
                            config.http_method = "GET"
                            allrevs_response = site.api(
                                http_method=config.http_method, **arv_params
                            )
                    except requests.exceptions.ReadTimeout as err:
                        # As above
                        print(f"ERROR: {str(err)}")
                        print("Sleeping for 20 seconds")
                        time.sleep(20)
                        # But avoid rewriting the same revisions
                        allrevs_response["query"]["allrevisions"] = []
                        continue
                else:
                    # End of continuation. We are done with this namespace.
                    break


def getXMLRevisionsByTitles(config: Config, session: requests.Session, site: mwclient.Site, start=None):
    if config.curonly:
        # The raw XML export in the API gets a title and gives the latest revision.
        # We could also use the allpages API as generator but let's be consistent.
        print("Getting titles to export the latest revision for each")
        c = 0
        for title in read_titles(config, session=session, start=start):
            # TODO: respect verbose flag, reuse output from getXMLPage
            print(f"    {title}")
            # TODO: as we're doing one page and revision at a time, we might
            # as well use xml format and exportnowrap=1 to use the string of,
            # XML as is, but need to check how well the library handles it.
            exportparams = {
                "action": "query",
                "titles": title,
                "export": "1",
            }
            try:
                export_response = site.api(
                    http_method=config.http_method, **exportparams
                )
            except requests.exceptions.HTTPError as e:
                if (
                        e.response.status_code == 405
                        and config.http_method == "POST"
                ):
                    print("POST request to the API failed, retrying with GET")
                    config.http_method = "GET"
                    export_response = site.api(
                        http_method=config.http_method, **exportparams
                    )
                else:
                    raise

            xml = str(export_response["query"]["export"]["*"])
            c += 1
            if c % 10 == 0:
                print(f"\n->  Downloaded {c} pages\n")
            # Because we got the fancy XML from the JSON format, clean it:
            yield make_xml_page_from_raw(xml, None)
    else:
        # This is the closest to what we usually do with Special:Export:
        # take one title at a time and try to get all revisions exported.
        # It differs from the allrevisions method because it actually needs
        # to be input the page titles; otherwise, the requests are similar.
        # The XML needs to be made manually because the export=1 option
        # refuses to return an arbitrary number of revisions (see above).
        print("Getting titles to export all the revisions of each")
        c = 0
        titlelist = []
        # TODO: Decide a suitable number of a batched request. Careful:
        # batched responses may not return all revisions.
        for titlelist in read_titles(config, session=session, start=start):
            if isinstance(titlelist, str):
                titlelist = [titlelist]
            for title in titlelist:
                print(f"    {title}")
            # Try and ask everything. At least on MediaWiki 1.16, uknown props are discarded:
            # "warnings":{"revisions":{"*":"Unrecognized values for parameter 'rvprop': userid, sha1, contentmodel"}}}
            pparams = {
                "action": "query",
                "titles": "|".join(titlelist),
                "prop": "revisions",
                'rvlimit': config.api_chunksize,
                "rvprop": "ids|timestamp|user|userid|size|sha1|contentmodel|comment|content|flags",
            }
            try:
                api_response = site.api(http_method=config.http_method, **pparams)
            except requests.exceptions.HTTPError as e:
                if (
                        e.response.status_code == 405
                        and config.http_method == "POST"
                ):
                    print("POST request to the API failed, retrying with GET")
                    config.http_method = "GET"
                    api_response = site.api(
                        http_method=config.http_method, **pparams
                    )
                else:
                    raise
            except mwclient.errors.InvalidResponse:
                log_error(
                    config=config, to_stdout=True,
                    text="Error: page inaccessible? Could not export page: %s"
                         % ("; ".join(titlelist)),
                )
                continue

            # Be ready to iterate if there is continuation.
            while True:
                # Get the revision data returned by the API: prequest is the initial request
                # or the new one after continuation at the bottom of this while loop.
                # The array is called "pages" even if there's only one.
                try:
                    pages = api_response["query"]["pages"]
                except KeyError:
                    log_error(
                        config=config, to_stdout=True,
                        text="Error: page inaccessible? Could not export page: %s"
                             % ("; ".join(titlelist)),
                    )
                    break
                # Go through the data we got to build the XML.
                for pageid in pages:
                    try:
                        xml = make_xml_from_page(pages[pageid], None)
                        yield xml
                    except PageMissingError:
                        log_error(
                            config=config, to_stdout=True,
                            text="Error: empty revision from API. Could not export page: %s"
                                 % ("; ".join(titlelist)),
                        )
                        continue

                # Get next batch of revisions if there's more.
                if "continue" in api_response.keys():
                    print("Getting more revisions for the page")
                    for key, value in api_response["continue"].items():
                        pparams[key] = value
                elif "query-continue" in api_response.keys():
                    rvstartid = api_response["query-continue"]["revisions"]["rvstartid"]
                    pparams["rvstartid"] = rvstartid
                else:
                    break

                try:
                    api_response = site.api(
                        http_method=config.http_method, **pparams
                    )
                except requests.exceptions.HTTPError as e:
                    if (
                            e.response.status_code == 405
                            and config.http_method == "POST"
                    ):
                        print("POST request to the API failed, retrying with GET")
                        config.http_method = "GET"
                        api_response = site.api(
                            http_method=config.http_method, **pparams
                        )

            # We're done iterating for this title or titles.
            c += len(titlelist)
            # Reset for the next batch.
            titlelist = []
            if c % 10 == 0:
                print(f"\n->  Downloaded {c} pages\n")


def getXMLRevisions(config: Config, session: requests.Session, lastPage: Optional[lxml.etree._ElementTree]=None, useAllrevision=True):
    # FIXME: actually figure out the various strategies for each MediaWiki version
    apiurl = urlparse(config.api)
    site = mwclient.Site(
        apiurl.netloc, apiurl.path.replace("api.php", ""), scheme=apiurl.scheme, pool=session
    )

    if useAllrevision:
        # Find last title
        if lastPage is not None:
            try:
                lastNs = int(lastPage.find('ns').text) # type: ignore
                if False:
                    lastRevision = lastPage.find('revision')
                    lastTimestamp = lastRevision.find('timestamp').text
                    lastRevid = int(lastRevision.find('id').text)
                    lastDatetime = datetime.fromisoformat(lastTimestamp.rstrip('Z'))
                    lastArvcontinue = lastDatetime.strftime("%Y%m%d%H%M%S") + '|' + str(lastRevid)
                else:
                    lastArvcontinue = lastPage.attrib['arvcontinue']
            except Exception:
                print("Failed to find title in last trunk XML: %s" % (lxml.etree.tostring(lastPage)))
                raise
            nscontinue = lastNs
            arvcontinue = lastArvcontinue
            if not arvcontinue:
                arvcontinue = None
        else:
            nscontinue = None
            arvcontinue = None

        try:
            return getXMLRevisionsByAllRevisions(config, session, site, nscontinue, arvcontinue)
        except (KeyError, mwclient.errors.InvalidResponse) as e:
            print(e)
            # TODO: check whether the KeyError was really for a missing arv API
            print("Warning. Could not use allrevisions. Wiki too old? Try to use --xmlrevisions_page")
            sys.exit(1)
    else:
        # Find last title
        if lastPage is not None:
            try:
                start = lastPage.find('title') # type: ignore
            except Exception:
                print("Failed to find title in last trunk XML: %s" % (lxml.etree.tostring(lastPage)))
                raise
        else:
            start = None

        try:
            # # Uncomment these lines to raise an KeyError for testing
            # raise KeyError(999999)
            # # DO NOT UNCOMMMENT IN RELEASE
            return getXMLRevisionsByTitles(config, session, site, start)
        except mwclient.errors.MwClientError as e:
            print(e)
            print("This mwclient version seems not to work for us. Exiting.")
            sys.exit(1)


def handle_infinite_loop(allrevs_response: Dict, arv_params: Dict, config: Config, site: mwclient.Site) -> Dict:
    """
    return new allrevs_response without arvprop=content|comment if the response is truncated
    """

    assert len(allrevs_response["query"]["allrevisions"]) == 0, \
        "We should have received no revisions if we are stuck in a infinite loop"
    print("WARNING: API returned continue parameter that doesn't change, we might be stuck in a loop")
    print(f"current continue parameter: {arv_params.get('arvcontinue')}")
    print(f"API warnings: {allrevs_response.get('warnings', {})}")

    if "truncated" in allrevs_response.get("warnings",{}).get("result",{}).get("*",""):
        # workaround for [truncated API requests for "allrevisions" causes infinite loop ]
        # (https://github.com/mediawiki-client-tools/mediawiki-scraper/issues/166)
        print("Let's try to skip this revision and continue...")
        _arv_params_temp = arv_params.copy()
        # make sure response is small
        _arv_params_temp['arvprop'] = _arv_params_temp['arvprop'].replace('|content', '').replace('|comment', '') 
        _arv_params_temp["arvlimit"] = 1

        allrevs_response_new = site.api(
            http_method=config.http_method, **_arv_params_temp
        )
        assert len(allrevs_response_new["query"]["allrevisions"]) == 1, \
            "Couldn't get a single revision to skip the infinite loop" # arvlimit=1
        assert arv_params.get("arvcontinue", None) != allrevs_response_new.get("continue", {}).get("arvcontinue", None), \
            "??? Infinite loop is still there ???"
        # success, let's continue
        log_error(config=config, to_stdout=True,
                text=f"ERROR: API returned continue parameter '{arv_params.get('arvcontinue')}' that doesn't change, "
                f"skipped this revision to avoid infinite loop")
        return allrevs_response_new
    else:
        raise NotImplementedError("Unable to solve the infinite loop automatically")
