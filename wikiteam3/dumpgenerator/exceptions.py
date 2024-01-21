from typing import Optional


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
        return "File '%s' sha1 is not match '%s'." % (self.file, self.excpected_sha1)
