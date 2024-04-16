from typing import Optional


class InternalApiError(Exception):
    """ base class for all internal API errors """
    error_code = "internal_api_error_*"
    errorclass = "MW*Exception"
    common_cause = "reason a; reason b; reason c"
    samples = ["url"]


class MWUnknownContentModelException(InternalApiError):
    error_code = "internal_api_error_MWUnknownContentModelException"
    errorclass = "MWUnknownContentModelException"
    common_cause = "The content model xxxxx is not registered on this wiki; Some extensions use special content models for their own purposes, but they did not register a handler to export their content (?)"
    samples = [
        "https://web.archive.org/web/20231015082428id_/https://www.wikidoc.org/api.php?titles=Talk%3AMain_Page&action=query&format=xml&prop=revisions&rvprop=timestamp|user|comment|content|ids|flags|size|userid|sha1|contentmodel&rvlimit=50",
        "https://web.archive.org/web/20231015082600id_/https://www.wikidoc.org/api.php?titles=Talk%3AMain_Page&action=query&format=json&prop=revisions&rvprop=timestamp|user|comment|content|ids|flags|size|userid|sha1|contentmodel&rvlimit=50"
    ]


class PageMissingError(Exception):
    def __init__(self, title, xml):
        self.title = title
        self.xml = xml

    def __str__(self):
        return "page '%s' not found" % self.title


class ExportAbortedError(Exception):
    def __init__(self, index):
        self.index = index

    def __str__(self):
        return "Export from '%s' did not return anything." % self.index


class FileSizeError(Exception):
    def __init__(self, file: str, got_size: int, excpected_size: int, online_url: Optional[str] = None):
        self.file = file
        self.got_size = got_size
        self.excpected_size = excpected_size
        self.online_url = online_url

    def __str__(self):
        return f"File '{self.file}' size {self.got_size} is not match '{self.excpected_size}'." \
            + (f"(url: {self.online_url})" if self.online_url else "")


class FileSha1Error(Exception):
    def __init__(self, file, excpected_sha1):
        self.file = file
        self.excpected_sha1 = excpected_sha1

    def __str__(self):
        return f"File '{self.file}' sha1 is not match '{self.excpected_sha1}'."
