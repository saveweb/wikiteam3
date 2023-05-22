'''
Extracts all titles from a XML dump file and writes them to `*-xml2titles.txt`.

requirements:
    file_read_backwards
    tqdm
'''

import dataclasses
import timeit
import io
import os
import argparse
import tqdm
import sys
# import re
import xml.sax
from xml.sax.saxutils import unescape

from file_read_backwards import FileReadBackwards


'''
  <page>
    <title>abcde</title>
    <ns>0</ns>
    <id>107</id>
    <revision>
      <id>238</id>
      <timestamp>2021-08-15T23:07:10Z</timestamp>
      <contributor>
        <username>user</username>
        <id>3</id>
      </contributor>
      <comment/>
      <model>wikitext</model>
      <format>text/x-wiki</format>
      <text xml:space="preserve" bytes="2326">text</text>
    </revision>
  </page>
'''
class XMLBaseHandler(xml.sax.handler.ContentHandler):
    '''only work on level <= 3 of the XML tree'''

    fileSize = 0

    class page__:
        # TODO
        pass

    def __init__(self, fileSize=0):
        self.fileSize = fileSize
        self.tqdm_progress = tqdm.tqdm(
            total=self.fileSize, unit="B", unit_scale=True, unit_divisor=1024, desc="Parsing XML"
        )
        self.tqdm_updated = 0
        self.globalParsedBytes = 0
        self.debugCount = 0
        self.silent = False

        self.depth = 0

        # page
        self.inPage = False
        self.page = {}
        self.pageTagsCount = 0
        self.pageRevisionsCount = 0

        # title
        self.inTitle = False
        self.title = None
        self.titleTagsCount = 0

        # ns
        self.inNs = False
        self.ns = None
        self.nsTagsCount = 0

        # id
        self.inId = False
        self.id = None
        self.idTagsCount = 0

        # revision
        self.inRevision = False
        self.revisionTagsCount = 0

    def close_tqdm(self):
        self.tqdm_progress.update(self.globalParsedBytes - self.tqdm_updated)
        self.tqdm_progress.close()
    
    def __debugCount(self):
        self.debugCount += 1
        print(self.debugCount)

    def resetPageTag(self):
        self.title = self.ns = self.id = None
        self.pageRevisionsCount = 0
        # print("resetPageTag")

    def startElement(self, name, attrs):
        self.globalParsedBytes += len(name)+2 + self.depth*2# +2 for '<' and '>'; *2 for ' ' space
        if len(attrs) > 0:
            str_total = 0
            str_total += sum([len(str(k))+len(str(v))+4 for k,v in attrs.items()])
            self.globalParsedBytes += str_total


        self.depth+=1
        if self.depth > 3:
            self.startElementOverDepth3(name, attrs)
            return
        
        if name == "page":
            self.inPage = True
            self.pageTagsCount += 1
        if name == "title":
            self.inTitle = True
            self.titleTagsCount += 1
        if name == "ns":
            self.inNs = True
            self.nsTagsCount += 1
        if name == "id":
            self.inId = True
            self.idTagsCount += 1
        if name == "revision":
            self.inRevision = True
            self.pageRevisionsCount += 1
            self.revisionTagsCount += 1

    def endElement(self, name):
        ''' if depth > 3, call endElementOverDepth3()\n
            if Element is page, call resetPageTag()
        '''
        self.globalParsedBytes += len(name) + 2
        # +3 for '</', '>'


        if self.depth > 3:
            self.endElementOverDepth3(name)
            self.depth-=1
            return
        self.depth-=1
        if name == "page":
            self.inPage = False

            if self.title is not None:
                self.page["title"] = self.title
            if self.ns is not None:
                self.page["ns"] = self.ns
            if self.id is not None:
                self.page["id"] = self.id
            if self.pageRevisionsCount is not None:
                self.page["revisionsCount"] = self.pageRevisionsCount

            self.resetPageTag()
        if name == "title":
            self.inTitle = False
        if name == "ns":
            self.inNs = False
        if name == "id":
            self.inId = False
        if name == "revision":
            self.inRevision = False

    def characters(self, content: str, not_parse_tags=["?"]):
        bufferSize = len(content.encode("utf-8"))
        self.globalParsedBytes += bufferSize
        if self.globalParsedBytes > self.tqdm_updated + 1024*1024:
            self.tqdm_progress.update(self.globalParsedBytes - self.tqdm_updated)
            self.tqdm_updated = self.globalParsedBytes


        if self.inPage:
            pass
        if self.inTitle:
            # self.__debugCount()
            self.cjoin("title", content) if 'title' not in not_parse_tags else None
        if self.inNs:
            self.cjoin("ns", content) if 'ns' not in not_parse_tags else None
        if self.inId:
            self.cjoin("id", content) if 'id' not in not_parse_tags else None
        if self.inRevision:
            pass


    def endDocument(self):
        if self.depth != 0:
            raise RuntimeError("depth != 0 at the end of the XML document")

    def startElementOverDepth3(self, name, attrs):
        pass

    def endElementOverDepth3(self, name):
        pass
    
    def cjoin(self, obj: str, content):
        ''' self.obj = self.obj + content if self.obj is not None else content 

        obj: str

        NOTE: cjoin() has very low performance on large obj, please use io.StringIO instead.
        '''
        if hasattr(self, obj):
            if getattr(self, obj) is None:
                setattr(self, obj, content)
            else:
                # assert ''.join((getattr(self, obj), content)) == content if getattr(self, obj) is None else getattr(self, obj) + content
                setattr(self, obj, ''.join((getattr(self, obj), content)))
                pass
        else:
            raise AttributeError("XMLBaseHandler has no attribute %s" % obj)
            setattr(self, obj, content)


class TitlesHandler(XMLBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_titles = set()
        self.list_titles = []
    def endElement(self, name):
        super().endElement(name)
        if name == "page":
            if self.page['title'] is not None:
                if self.page['title'] in self.set_titles:
                    print("Duplicate title found: %s" % self.page['title']) if not self.silent else None
                else:
                    self.set_titles.add(self.page['title'])
                    self.list_titles.append(self.page['title']) # unique
                    if not self.silent:
                        print(self.page)

class RevsHandler(XMLBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rev = {}
        self.revtextAttrs = []
        self.revtextRealLength = 0

        # text
        self.inText = False
        self.revText: io.StringIO = io.StringIO()
        self.textTagsCount = 0
        # sha1
        self.inSha1 = False
        self.revSha1: str = ''


    # TODO
    def startElementOverDepth3(self, name, attrs):
        # super().startElementOverDepth3(name, attrs)

        # text
        if name == 'text' and attrs:
            self.revtextAttrs = dict(attrs)
            self.rev['textAttrs'] = self.revtextAttrs
        if name == 'text':
            self.inText = True
            self.textTagsCount += 1

        # sha1
        if name == 'sha1':
            self.inSha1 = True
    
    def endElementOverDepth3(self, name):

        # super().endElementOverDepth3(name)
        if name == 'text':
            self.inText = False
        if name == 'sha1':
            self.inSha1 = False

    def resetRevTag(self):
        self.revtextAttrs = {}
        self.globalParsedBytes += self.revtextRealLength
        self.revtextRealLength = 0
        self.revText: io.StringIO = io.StringIO()
        self.revSha1 = ''


    def endElement(self, name):
        if name == 'text':
            self.revtextRealLength = len(self.revText.getvalue().encode('utf-8')) if self.revText is not None else 0
            self.rev['textRealLength'] = self.revtextRealLength
        if name == "revision":
            print(self.rev, self.title, self.revSha1)
            self.resetRevTag()
        super().endElement(name)


    def characters(self, content):
        if self.inSha1:
            self.cjoin('revSha1', content)
        elif self.inText:
            self.revText.write(content)
        else:
            super().characters(content)



class MediaNsHandler(XMLBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.mediaNsPages = []
        self.mediaNsPagesName_set = set()
        self.mediaNsPagesID_set = set()
    def endElement(self, name):
        super().endElement(name)
        if name == "page":
            if self.page['ns'] == '6':
                if self.page['title'] in self.mediaNsPagesName_set:
                    if not self.silent:
                        print("Duplicate title found: %s" % self.page['title'])
                else:
                    self.mediaNsPagesName_set.add(self.page['title'])
                    # self.mediaNsPages.append(self.page)
                    # print(self.page)
                if self.page['id'] in self.mediaNsPagesID_set:
                    if not self.silent:
                        print("Duplicate id found: %s" % self.page['id'])
                else:
                    self.mediaNsPagesID_set.add(self.page['id'])
                    # self.mediaNsPages.append(self.page)
                    print(self.page)

def get_titles_from_xml(xmlfile, return_type="list", silent=False):
    '''Return a list/set of titles from a XML dump file.\n
    `xmlfile`: a system identifier or an InputSource.\n
    `return_type`:`"list"` or `"set"` (default: `"list"`).
    The `list` keeps the order of XML file, and is unique.
    '''
    # xmlfile_size = os.path.getsize(xmlfile)
    parse_start = timeit.default_timer()
    parser = xml.sax.make_parser()
    handler = TitlesHandler(os.path.getsize(xmlfile))
    # handler = RevsHandler(os.path.getsize(xmlfile)) # TODO
    # handler = MediaNsHandler(os.path.getsize(xmlfile)) # TODO
    handler.silent = silent
    parser.setContentHandler(handler)
    parser.parse(xmlfile)
    handler.close_tqdm()
    print('',flush=True)
    print('pageTagsCount:', handler.pageTagsCount,
            'titleTagsCount:', handler.titleTagsCount,
            'nsTagsCount:', handler.nsTagsCount,
            'idTagsCount:', handler.idTagsCount,
            'revisionTagsCount:', handler.revisionTagsCount)
    # print('MediaNsPages (Name):', len(handler.mediaNsPagesName_set))
    # print('MediaNsPages (ID):', len(handler.mediaNsPagesID_set))
    parse_end = timeit.default_timer()
    print('Parse time:', parse_end - parse_start)
    if len(handler.set_titles) != len(handler.list_titles):
        raise RuntimeError("len(set_titles) and (list_titles) are not equal!")

    titles = handler.set_titles if return_type == "set" else handler.list_titles
    
    return titles


@dataclasses.dataclass
class Config:
    xmlfile: str
    dry: bool
    verbose: bool

def getArguments():
    parser = argparse.ArgumentParser()

    parser.description = "Extracts all titles from a XML dump file and writes them to `*-xml2titles.txt`."
    parser.add_argument("xmlfile", help="XML file of wiki dump")
    parser.add_argument("--dry", help="Do not write to file",action="store_true")
    parser.add_argument("--verbose", help="Verbose",action="store_true")

    args = parser.parse_args()
    config = Config
    config.xmlfile = args.xmlfile
    config.dry = args.dry
    config.verbose = args.verbose

    return config


if __name__ == "__main__":
    args = getArguments()

    print('Parsing...')

    xmlfile = args.xmlfile
    if not os.path.exists(xmlfile):
        print("XML file does not exist!")
        sys.exit(1)

    xml_basename = os.path.basename(xmlfile)
    xml_dir = os.path.dirname(xmlfile)

    assert xml_basename.endswith(".xml")
    "XML file name does not end with .xml!"
    assert xml_basename.endswith("-current.xml") or xml_basename.endswith("-history.xml")
    "XML file name does not end with -current.xml or -history.xml!"

    with FileReadBackwards(xmlfile, encoding='utf-8') as frb:
        seeked = 0
        for line in frb:
            seeked += 1
            if "</mediawiki>" in line:
                # xml dump is complete
                break
            if seeked > 4:
                raise Exception('xml dump is incomplete!')

    _silent = not args.verbose

    titles = get_titles_from_xml(xmlfile=xmlfile, return_type="list", silent=_silent)

    if args.dry:
        print("Dry run. No file will be written.")
        sys.exit(0)

    titles_filename = xml_basename.replace("-current.xml", "-xml2titles.txt").replace("-history.xml", "-xml2titles.txt")
    titles_filepath = os.path.join(xml_dir, titles_filename)
    with open(titles_filepath, "w") as f:
        f.write("\n".join(titles))
        f.write("\n--END--\n")

    print("Done! %d titles extracted to %s" % (len(titles), titles_filepath))
