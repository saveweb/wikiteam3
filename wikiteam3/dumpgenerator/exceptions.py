from typing import List, Optional, Type
import requests

from wikiteam3.dumpgenerator.api.get_json import get_JSON


def InternalApiError_autohandler(response: requests.Response, json = False, xml = False) -> None:
    """ raise the appropriate InternalApiError exception for an internal API error """
    ErrorClasses: List[Type[InternalApiError]] = [MWUnknownContentModelException] # type: ignore
    if json:
        try:
            error_code = get_JSON(response).get('error', {}).get('code', '')
        except Exception:
            print("failed to load JSON")
            return
        for IAE in ErrorClasses:
            if error_code == IAE.error_code:
                raise IAE(response)

    elif xml and b"</error>" in response.content:
        for IAE in ErrorClasses:
            if f"code=\"{IAE.error_code}\"".encode("utf-8") in response.content:
                raise IAE(response)
    else:
        pass # do nothing


class PageMissingError(Exception):
    def __init__(self, title, xml):
        self.title = title
        self.xml = xml

    def __str__(self):
        return "page '%s' not found" % self.title


class InternalApiError(Exception):
    """ base class for all internal API errors """
    error_code = "internal_api_error_*"
    errorclass = "MW*Exception"
    common_cause = "reason a; reason b; reason c"
    samples = ["url"]

    def __init__(self, response: Optional[requests.Response] = None, alt_text: Optional[str] = None):
        """ pass alt_text if we don't have a response """
        self.response = response
        self.alt_text = alt_text

    def __str__(self):
        return f"internal API error ({self.__class__.__name__}): '{self.response.url if self.response else self.alt_text}'"

class MWUnknownContentModelException(InternalApiError):
    error_code = "internal_api_error_MWUnknownContentModelException"
    errorclass = "MWUnknownContentModelException"
    common_cause = "The content model xxxxx is not registered on this wiki; Some extensions use special content models for their own purposes, but they did not register a handler to export them (?)."
    samples = [
        "https://web.archive.org/web/20231015082428id_/https://www.wikidoc.org/api.php?titles=Talk%3AMain_Page&action=query&format=xml&prop=revisions&rvprop=timestamp|user|comment|content|ids|flags|size|userid|sha1|contentmodel&rvlimit=50",
        "https://web.archive.org/web/20231015082600id_/https://www.wikidoc.org/api.php?titles=Talk%3AMain_Page&action=query&format=json&prop=revisions&rvprop=timestamp|user|comment|content|ids|flags|size|userid|sha1|contentmodel&rvlimit=50"
    ]



class ExportAbortedError(Exception):
    def __init__(self, index):
        self.index = index

    def __str__(self):
        return "Export from '%s' did not return anything." % self.index


class FileSizeError(Exception):
    def __init__(self, file, excpected_size):
        self.file = file
        self.excpected_size = excpected_size

    def __str__(self):
        return f"File '{self.file}' size is not match '{self.excpected_size}'."


class FileSha1Error(Exception):
    def __init__(self, file, excpected_sha1):
        self.file = file
        self.excpected_sha1 = excpected_sha1

    def __str__(self):
        return "File '%s' sha1 is not match '%s'." % (self.file, self.excpected_sha1)
